"""Motor que convierte una configuración (JSON) + fotos + música en una invitación lista para publicar."""
import base64
import colorsys
import copy
import io
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
import zipfile
from datetime import date, datetime, time, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from PIL import Image, ImageDraw, ImageFont, ImageOps

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ / "plantilla"
FUENTES = Path(__file__).resolve().parent / "fuentes"

# ---------------------------------------------------------------- paletas
# El diseño base es gris azulado (tono ~210°). Cada paleta gira el tono y ajusta la saturación
# de todos los colores del diseño, conservando su luminosidad: así el contraste nunca se pierde.
TONO_BASE = 210
PALETAS = {
    "Gris azulado": {"tono": 210, "saturacion": 1.0},
    "Negro y plata": {"tono": 210, "saturacion": 0.22},
    "Marfil y dorado": {"tono": 40, "saturacion": 1.45},
    "Champaña": {"tono": 32, "saturacion": 0.85},
    "Verde salvia": {"tono": 110, "saturacion": 0.85},
    "Verde olivo": {"tono": 75, "saturacion": 1.3},
    "Rosa palo": {"tono": 350, "saturacion": 1.0},
    "Terracota": {"tono": 18, "saturacion": 1.6},
    "Vino": {"tono": 345, "saturacion": 1.8},
    "Azul marino": {"tono": 222, "saturacion": 2.0},
    "Lavanda": {"tono": 265, "saturacion": 1.1},
    "Lila": {"tono": 285, "saturacion": 0.9},
    "Esmeralda": {"tono": 155, "saturacion": 1.5},
    "Menta": {"tono": 160, "saturacion": 0.9},
    "Turquesa": {"tono": 184, "saturacion": 1.6},
    "Coral": {"tono": 8, "saturacion": 1.6},
    "Durazno": {"tono": 22, "saturacion": 1.15},
    "Mostaza": {"tono": 45, "saturacion": 2.1},
    "Chocolate": {"tono": 25, "saturacion": 0.75},
    "Arena": {"tono": 38, "saturacion": 0.55},
}

# Estilos base: cambian adornos, fondos y formas; cada uno sugiere paleta, letras y efectos.
ESTILOS = {
    "clasico": {"nombre": "Clásico elegante", "paleta": "Gris azulado", "fuente_script": "Pinyon Script", "fuente_serif": "Cormorant Garamond",
                "fuente_sans": "Montserrat", "sello": "negro", "efectos": {"fondo": "petalos", "apertura": "petalos", "final": "fuegos", "toque": False}},
    "playa": {"nombre": "Playa", "paleta": "Turquesa", "fuente_script": "Sacramento", "fuente_serif": "Lora",
              "fuente_sans": "Quicksand", "sello": "azul", "efectos": {"fondo": "burbujas", "apertura": "destellos", "final": "confeti", "toque": True}},
    "rustico": {"nombre": "Rústico", "paleta": "Verde olivo", "fuente_script": "Dancing Script", "fuente_serif": "EB Garamond",
                "fuente_sans": "Josefin Sans", "sello": "chocolate", "efectos": {"fondo": "hojas", "apertura": "petalos", "final": "linternas", "toque": False}},
    "moderno": {"nombre": "Moderno minimalista", "paleta": "Negro y plata", "fuente_script": "Italianno", "fuente_serif": "Bodoni Moda",
                "fuente_sans": "Poppins", "sello": "negro", "efectos": {"fondo": "destellos", "apertura": "destellos", "final": "fuegos", "toque": True}},
}

EFECTOS_FONDO = {"petalos": "Pétalos blancos", "corazones": "Corazones", "luciernagas": "Luciérnagas", "destellos": "Destellos",
                 "nieve": "Nieve", "hojas": "Hojas", "burbujas": "Burbujas", "confeti": "Confeti", "ninguno": "Ninguno"}
EFECTOS_APERTURA = {"petalos": "Lluvia de pétalos", "confeti": "Confeti", "destellos": "Destellos", "corazones": "Corazones", "ninguno": "Ninguno"}
EFECTOS_FINAL = {"fuegos": "Fuegos artificiales", "confeti": "Cañones de confeti", "linternas": "Linternas flotantes",
                 "corazones": "Lluvia de corazones", "destellos": "Estallidos de destellos", "ninguno": "Ninguno"}

# Color de la cera del sello: (sello en SVG: 3 tonos + 2 interiores) y (sello 3D: 3 tonos + lateral)
SELLOS = {
    "negro": None,
    "vino": (["#8c3b4a", "#4d1420", "#1e0509", "#5a1f2b", "#2a0a10"], ["#b0405a", "#6a1a2c", "#26070e", "0x4a1220"]),
    "verde": (["#4f6b52", "#1f3323", "#08120a", "#2c4230", "#0f1a11"], ["#6a9a70", "#2c4c33", "#0c1a0f", "0x1f3324"]),
    "azul": (["#4a5f80", "#1b2a44", "#070d18", "#26375a", "#0c1424"], ["#6582b8", "#273c66", "#0b1426", "0x1a2a4a"]),
    "chocolate": (["#7a5a44", "#3b2618", "#140b06", "#4a3222", "#1c120b"], ["#9c7556", "#4c3322", "#1a0e08", "0x36251a"]),
}
_SELLO_HTML = ["#666c74", "#26292d", "#050506", "#34383d", "#111315"]
_SELLO_3D = ["#3b4047", "#17191c", "#050506", "0x0c0d0f"]

def cambiar_sello(texto, sello, tono, sat, es_js=False):
    if not SELLOS.get(sello):
        return texto
    base = _SELLO_3D if es_js else _SELLO_HTML
    nuevo = SELLOS[sello][1 if es_js else 0]
    for viejo, n in zip(base, nuevo):
        texto = texto.replace(recolorear(viejo, tono, sat), n)
    return texto

def _recolor_rgb(r, g, b, tono, sat):
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn < 8:                      # neutros (blancos, negros, grises puros) se quedan igual
        return r, g, b
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    hd = h * 360
    if not (170 <= hd <= 260):           # solo se mueven los colores de la familia gris azulado
        return r, g, b
    nh = ((tono + (hd - TONO_BASE)) % 360) / 360
    ns = max(0.0, min(1.0, s * sat))
    rr, gg, bb = colorsys.hls_to_rgb(nh, l, ns)
    return round(rr * 255), round(gg * 255), round(bb * 255)

def recolorear(texto, tono, sat):
    if tono == TONO_BASE and abs(sat - 1) < 1e-6:
        return texto
    def hexrep(m):
        h = m.group(1)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r, g, b = _recolor_rgb(r, g, b, tono, sat)
        out = f"{r:02x}{g:02x}{b:02x}"
        return m.group(0)[: -6] + out
    texto = re.sub(r"(?<![0-9a-zA-Z_])#([0-9a-fA-F]{6})(?![0-9a-fA-F])", hexrep, texto)
    texto = re.sub(r"(?<![0-9a-zA-Z_])0x([0-9a-fA-F]{6})(?![0-9a-fA-F])", hexrep, texto)
    def rgbrep(m):
        r, g, b = int(m.group(2)), int(m.group(3)), int(m.group(4))
        r, g, b = _recolor_rgb(r, g, b, tono, sat)
        return f"{m.group(1)}({r},{g},{b}{m.group(5)}"
    texto = re.sub(r"(rgba?)\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(\s*[,)])", rgbrep, texto)
    return texto

def muestra_paleta(tono, sat):
    """Colores representativos para enseñar la paleta en el editor."""
    base = ["#111214", "#3f5163", "#6b7f93", "#b3c1ce", "#eef1f4", "#ffffff"]
    return [recolorear(c, tono, sat) for c in base]

# ---------------------------------------------------------------- tipografías
FUENTES_SCRIPT = {
    "Pinyon Script": "PinyonScript.ttf",
    "Great Vibes": "GreatVibes.ttf",
    "Parisienne": "Parisienne.ttf",
    "Alex Brush": "AlexBrush.ttf",
    "Allura": "Allura.ttf",
    "Dancing Script": "DancingScript.ttf",
    "Sacramento": "Sacramento.ttf",
    "Italianno": "Italianno.ttf",
    "Tangerine": "Tangerine.ttf",
}
FUENTES_SERIF = {
    "Cormorant Garamond": "ital,wght@0,300;0,400;0,500;0,600;1,300;1,400",
    "Playfair Display": "ital,wght@0,400;0,500;0,600;1,400",
    "EB Garamond": "ital,wght@0,400;0,500;0,600;1,400",
    "Lora": "ital,wght@0,400;0,500;0,600;1,400",
    "Bodoni Moda": "ital,wght@0,400;0,500;0,600;1,400",
    "Libre Baskerville": "ital,wght@0,400;0,700;1,400",
    "Cinzel": "wght@400;500;600",
    "Marcellus": "",
}
FUENTES_SANS = {
    "Montserrat": "wght@300;400;500",
    "Raleway": "wght@300;400;500",
    "Josefin Sans": "wght@300;400;500",
    "Lato": "wght@300;400;700",
    "Poppins": "wght@300;400;500",
    "Quicksand": "wght@300;400;500",
    "Nunito Sans": "wght@300;400;500",
}

def url_fuentes(serif, script, sans):
    q = lambda n: n.replace(" ", "+")
    fam = lambda n, spec: q(n) + (":" + spec if spec else "")
    return ("https://fonts.googleapis.com/css2?family=" + fam(serif, FUENTES_SERIF[serif])
            + "&family=" + q(script) + "&family=" + fam(sans, FUENTES_SANS[sans]) + "&display=swap")

def cambiar_fuentes(texto, serif, script, sans):
    for viejo, nuevo in (("Cormorant Garamond", serif), ("Pinyon Script", script), ("Montserrat", sans)):
        if viejo != nuevo:
            texto = texto.replace(viejo, nuevo)
    return texto

# ---------------------------------------------------------------- fechas en español
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
ZONAS = {
    "Centro (CDMX, Jalisco, Colima…) -06:00": "-06:00",
    "Pacífico (Sinaloa, Sonora, Nayarit…) -07:00": "-07:00",
    "Noroeste (Baja California) -08:00": "-08:00",
    "Sureste (Quintana Roo) -05:00": "-05:00",
}

def _fecha(v):
    return v if isinstance(v, date) else date.fromisoformat(v)

def _hora(v):
    return v if isinstance(v, time) else time.fromisoformat(v)

def slugify(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") or "invitacion"

def telefono_bonito(t):
    t = re.sub(r"\D", "", t or "")
    return f"{t[0:3]} {t[3:6]} {t[6:]}" if len(t) == 10 else t

# ---------------------------------------------------------------- configuración de ejemplo
def config_ejemplo():
    return json.loads((RAIZ / "ejemplos" / "ejemplo.json").read_text(encoding="utf-8"))

def config_vacia():
    c = config_ejemplo()
    c["novios"] = {"nombre1": "Nombre 1", "nombre2": "Nombre 2", "monograma": "", "texto": ""}
    c["slug"] = "nueva-invitacion"
    c["site_url"] = ""
    c["fotos"] = []
    return c

def completar(c):
    """Rellena campos que falten con los del ejemplo (útil al abrir proyectos de versiones anteriores)."""
    base = config_ejemplo()
    def merge(a, b):
        for k, v in b.items():
            if k not in a:
                a[k] = copy.deepcopy(v)
            elif isinstance(v, dict) and isinstance(a[k], dict):
                merge(a[k], v)
    tenia_efectos = "efectos" in c
    merge(c, base)
    if not tenia_efectos:
        f = c.get("funciones", {})
        c["efectos"]["fondo"] = "petalos" if f.get("petalos", True) else "ninguno"
        c["efectos"]["apertura"] = "petalos" if f.get("petalos", True) else "ninguno"
        c["efectos"]["final"] = "fuegos" if f.get("fuegos", True) else "ninguno"
    return c

# ---------------------------------------------------------------- datos derivados
def derivar(c, galeria_nombres):
    n1, n2 = c["novios"]["nombre1"].strip(), c["novios"]["nombre2"].strip()
    texto = c["novios"].get("texto") or f"{n1} & {n2}"
    c["novios"]["texto"] = texto
    if not c["novios"].get("monograma"):
        c["novios"]["monograma"] = f"{n1[:1]}&{n2[:1]}"
    f = _fecha(c["fecha"])
    hi, hf = _hora(c["hora_inicio"]), _hora(c["hora_fin"])
    tz = c.get("zona", "-06:00")
    ini = datetime.combine(f, hi)
    fin = datetime.combine(f, hf)
    if fin <= ini:
        fin += timedelta(days=1)
    lim = c.get("fecha_limite")
    site = (c.get("site_url") or "").strip()
    if site and not site.endswith("/"):
        site += "/"
    # nombre de la portada letra por letra
    h1, t = [], 0.55
    for i, palabra in enumerate([n1, "&", n2]):
        if palabra == "&":
            h1.append(f'<span class="amp ch" style="animation-delay:{t:.2f}s">&amp;</span>')
            t += 0.15
        else:
            bloques = []
            for w in palabra.split():
                letras = "".join(f'<span class="ch" style="animation-delay:{t + k * 0.07:.2f}s">{ch}</span>' for k, ch in enumerate(w))
                bloques.append(f'<span style="white-space:nowrap;display:inline-block">{letras}</span>')
                t += len(w) * 0.07 + 0.05
            h1.append(" ".join(bloques))
            t += 0.05
    for p in c.get("contactos", []):
        p["telefono_bonito"] = telefono_bonito(p.get("telefono", ""))
    lugar_cal = ", ".join(x for x in [c["lugares"][0]["nombre"], c["lugares"][0]["direccion"]] if x) if c.get("lugares") else ""
    itin_txt = " · ".join(f'{i["titulo"]} {i["hora"]}' for i in c.get("itinerario", []))
    d = {
        "fecha_larga": f"{DIAS[f.weekday()].capitalize()} {f.day} de {MESES[f.month - 1]} de {f.year}",
        "fecha_corta": f"{f.day:02d} · {f.month:02d} · {f.year}",
        "fecha_hero": f"{f.day} · {MESES[f.month - 1].upper()} · {f.year}",
        "limite_dia": f"{_fecha(lim).day} de {MESES[_fecha(lim).month - 1]}" if lim else "",
        "limite_anio": f"de {_fecha(lim).year}" if lim else "",
        "site_url": site,
        "fonts_url": url_fuentes(c["diseno"]["fuente_serif"], c["diseno"]["fuente_script"], c["diseno"]["fuente_sans"]),
        "h1_html": " ".join(h1),
        "h1_style": "" if len(n1 + n2) <= 11 else f"font-size:clamp(2.4rem,{max(8, 15 * 11 / len(n1 + n2)):.1f}vw,6.5rem)",
        "galeria": galeria_nombres,
        "ics_nombre": f'{slugify(c["textos"]["titulo_evento"])}.ics',
    }
    d["js_config"] = {
        "novios": texto,
        "eventoDe": c["textos"]["evento_de"],
        "tituloEvento": c["textos"]["titulo_evento"],
        "fechaEvento": ini.strftime("%Y-%m-%dT%H:%M:%S") + tz,
        "finEvento": fin.strftime("%Y-%m-%dT%H:%M:%S") + tz,
        "lugarCalendario": lugar_cal,
        "descripcionCalendario": itin_txt,
        "slug": c.get("slug", "invitacion"),
        "musica": bool(c["musica"]["activa"]),
        "inicioCancion": float(c["musica"].get("inicio", 0) or 0),
        "volumen": float(c["musica"].get("volumen", 0.7) or 0.7),
        "funciones": c["funciones"],
        "efectos": c["efectos"],
        "monograma": c["novios"]["monograma"],
        "fechaCorta": d["fecha_corta"],
        "textos": {k: c["textos"][k] for k in ("hero_kicker", "pase_singular", "pase_plural", "copiado", "copiado_aviso")},
    }
    return d

# ---------------------------------------------------------------- fotos
def recorte(img, ratio, fx=0.5, fy=0.5, zoom=1.0):
    """Recorta a la proporción pedida centrando en el punto (fx, fy) con acercamiento."""
    W, H = img.size
    if W / H > ratio:
        h = H; w = h * ratio
    else:
        w = W; h = w / ratio
    w, h = w / max(zoom, 1), h / max(zoom, 1)
    cx, cy = fx * W, fy * H
    x0 = min(max(cx - w / 2, 0), W - w)
    y0 = min(max(cy - h / 2, 0), H - h)
    return img.crop((round(x0), round(y0), round(x0 + w), round(y0 + h)))

def _jpg(img, maxw=None, q=82):
    if maxw and img.width > maxw:
        img = img.resize((maxw, round(img.height * maxw / img.width)), Image.LANCZOS)
    b = io.BytesIO()
    img.convert("RGB").save(b, "JPEG", quality=q, optimize=True, progressive=True)
    return b.getvalue()

def abrir(b):
    return ImageOps.exif_transpose(Image.open(io.BytesIO(b))).convert("RGB")

def tile_es_horizontal(i):
    return i % 3 == 2

def procesar_fotos(c, fotos_bytes, ligero=False):
    """fotos_bytes: {id: bytes}. Devuelve {ruta: bytes} y la lista de la galería."""
    out, galeria = {}, []
    mx = 0.55 if ligero else 1.0
    fotos = [f for f in c.get("fotos", []) if f["id"] in fotos_bytes]
    portada = next((f for f in fotos if f.get("portada")), fotos[0] if fotos else None)
    previa = next((f for f in fotos if f.get("vista_previa")), portada)
    if portada:
        im = abrir(fotos_bytes[portada["id"]])
        pz = portada.get("zoom_portada", 1.0)
        out["fotos/portada.jpg"] = _jpg(recorte(im, 9 / 16, portada["fx"], portada["fy"], pz), int(1100 * mx))
        out["fotos/portada-h.jpg"] = _jpg(recorte(im, 16 / 10, portada["fx"], portada["fy"], 1.0), int(1800 * mx))
    if previa:
        im = abrir(fotos_bytes[previa["id"]])
        out["fotos/vista-previa.jpg"] = _jpg(recorte(im, 1200 / 630, previa["fx"], previa["fy"], previa.get("zoom_previa", 1.0)).resize((1200, 630), Image.LANCZOS), q=85)
    for f in [f for f in fotos if f.get("galeria", True)]:
        i = len(galeria)
        nombre = f"galeria{i + 1}.jpg"
        im = abrir(fotos_bytes[f["id"]])
        ratio = 16 / 10 if tile_es_horizontal(i) else 3 / 4
        out["fotos/" + nombre] = _jpg(recorte(im, ratio, f["fx"], f["fy"], f.get("zoom", 1.0)), int((1400 if ratio > 1 else 900) * mx))
        out["fotos/full/" + nombre] = _jpg(im, int(1600 * mx))
        galeria.append(nombre)
    return out, galeria

def icono(c):
    S = 360
    im = Image.new("RGB", (S, S), (11, 12, 13)); d = ImageDraw.Draw(im)
    claro = recolorear("#b3c1ce", c["diseno"]["tono"], c["diseno"]["saturacion"])
    medio = recolorear("#5a6876", c["diseno"]["tono"], c["diseno"]["saturacion"])
    d.ellipse((24, 24, S - 24, S - 24), outline=claro, width=3)
    d.ellipse((38, 38, S - 38, S - 38), outline=medio, width=1)
    fuente = FUENTES / FUENTES_SCRIPT.get(c["diseno"]["fuente_script"], "PinyonScript.ttf")
    t = c["novios"]["monograma"]
    size = 120
    while True:
        f = ImageFont.truetype(str(fuente), size)
        bb = d.textbbox((0, 0), t, font=f)
        if bb[2] - bb[0] <= 230 or size < 40:
            break
        size -= 6
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((S - w) / 2 - bb[0], (S - h) / 2 - bb[1] + 4), t, font=f, fill=(238, 243, 247))
    b = io.BytesIO(); im.resize((180, 180), Image.LANCZOS).save(b, "PNG", optimize=True)
    return b.getvalue()

# ---------------------------------------------------------------- música
def comprimir_musica(b, kbps=128):
    if not shutil.which("ffmpeg"):
        return b
    with tempfile.TemporaryDirectory() as td:
        src, dst = Path(td) / "in", Path(td) / "out.mp3"
        src.write_bytes(b)
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0:a", "-b:a", f"{kbps}k", "-ac", "2", str(dst)],
                           capture_output=True, timeout=180)
        return dst.read_bytes() if r.returncode == 0 and dst.exists() else b

# ---------------------------------------------------------------- generar
def _env():
    return Environment(loader=FileSystemLoader(str(PLANTILLA)), autoescape=True, trim_blocks=False)

def construir(c, fotos_bytes, musica_bytes=None, ligero=False):
    """Devuelve {ruta: bytes} con todos los archivos del sitio."""
    c = completar(copy.deepcopy(c))
    archivos, galeria = procesar_fotos(c, fotos_bytes, ligero)
    d = derivar(c, galeria)
    if not musica_bytes:
        c["musica"]["activa"] = False
        d["js_config"]["musica"] = False
    iconos = json.loads((PLANTILLA / "iconos.json").read_text(encoding="utf-8"))
    tono, sat = c["diseno"]["tono"], c["diseno"]["saturacion"]
    fs = (c["diseno"]["fuente_serif"], c["diseno"]["fuente_script"], c["diseno"]["fuente_sans"])
    html = _env().get_template("index.html.j2").render(c=c, d=d, iconos=iconos)
    html = cambiar_sello(cambiar_fuentes(recolorear(html, tono, sat), *fs), c["diseno"].get("sello", "negro"), tono, sat)
    archivos["index.html"] = html.encode("utf-8")
    if c["funciones"].get("sobre3d"):
        archivos["js/three.min.js"] = (PLANTILLA / "js" / "three.min.js").read_bytes()
        js = (PLANTILLA / "js" / "sobre3d.js").read_text(encoding="utf-8")
        js = cambiar_sello(cambiar_fuentes(recolorear(js, tono, sat), *fs), c["diseno"].get("sello", "negro"), tono, sat, es_js=True)
        archivos["js/sobre3d.js"] = js.encode("utf-8")
    archivos["js/efectos.js"] = recolorear((PLANTILLA / "js" / "efectos.js").read_text(encoding="utf-8"), tono, sat).encode("utf-8")
    archivos["fotos/icono.png"] = icono(c)
    if musica_bytes and c["musica"]["activa"]:
        archivos["musica.mp3"] = musica_bytes
    return archivos

def a_zip(archivos):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for ruta, data in sorted(archivos.items()):
            z.writestr(ruta, data)
    return b.getvalue()

def vista_previa(archivos, con_musica=False):
    """Un solo HTML con todo incrustado, para mostrarlo dentro de Streamlit."""
    html = archivos["index.html"].decode("utf-8")
    def data_uri(ruta, mime):
        return f"data:{mime};base64," + base64.b64encode(archivos[ruta]).decode()
    for ruta in sorted([r for r in archivos if r.startswith("fotos/") and r.endswith(".jpg")], key=len, reverse=True):
        html = html.replace(ruta, data_uri(ruta, "image/jpeg"))
    html = html.replace('href="fotos/icono.png"', 'href="' + data_uri("fotos/icono.png", "image/png") + '"')
    for js in ("js/efectos.js", "js/three.min.js", "js/sobre3d.js"):
        tag = f'<script src="{js}" defer></script>'
        if js in archivos and tag in html:
            code = archivos[js].decode("utf-8").replace("</script", "<\\/script")
            html = html.replace(tag, "<script>" + code + "</script>")
    if "musica.mp3" in archivos:
        html = html.replace('src="musica.mp3"', 'src="' + (data_uri("musica.mp3", "audio/mpeg") if con_musica else "") + '"')
    return html

# ---------------------------------------------------------------- invitados
def enlaces_invitados(site_url, filas):
    """filas: [(nombre, pases)] -> [{nombre, pases, enlace, mensaje}]"""
    from urllib.parse import quote
    site = site_url.rstrip("/") + "/"
    out = []
    for nombre, pases in filas:
        nombre = str(nombre).strip()
        if not nombre:
            continue
        p = str(pases).strip() if pases not in (None, "") else ""
        try:
            p = str(int(float(p))) if p else ""
        except ValueError:
            p = ""
        url = site + "?invitado=" + quote(nombre) + (f"&pases={p}" if p else "")
        out.append({"nombre": nombre, "pases": p, "enlace": url})
    return out
