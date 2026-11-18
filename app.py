"""Estudio de invitaciones digitales — editor en Streamlit.

Carga un proyecto (o empieza uno nuevo), edita datos, fotos, música y diseño,
mira la vista previa y descarga el .zip listo para Cloudflare Pages.
"""
import copy
import hashlib
import io
import json
import zipfile
from datetime import date, time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from motor import build

st.set_page_config(page_title="Estudio de invitaciones", page_icon="💌", layout="wide")

# ------------------------------------------------------------------ estado
ss = st.session_state
if "c" not in ss:
    ss.c = build.config_ejemplo()
    ss.fotos = {}          # id -> bytes originales
    ss.musica = None       # bytes ya comprimidos
    ss.rev = 0             # cambia al abrir un proyecto para reiniciar los controles
c = ss.c

def k(nombre):
    return f"{ss.rev}-{nombre}"

def nuevo_estado(config, fotos=None, musica=None):
    ss.c = build.completar(config)
    ss.fotos = fotos or {}
    ss.musica = musica
    ss.rev += 1
    ss.pop("preview_html", None)

ICONOS = list(json.loads((build.PLANTILLA / "iconos.json").read_text(encoding="utf-8")))

# ------------------------------------------------------------------ proyectos (.zip)
def proyecto_zip():
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_STORED) as z:
        z.writestr("config.json", json.dumps(c, ensure_ascii=False, indent=1, default=str))
        for fid, data in ss.fotos.items():
            z.writestr(f"fotos/{fid}", data)
        if ss.musica:
            z.writestr("musica.mp3", ss.musica)
    return b.getvalue()

def abrir_proyecto(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        config = json.loads(z.read("config.json").decode("utf-8"))
        fotos = {n.split("/", 1)[1]: z.read(n) for n in z.namelist() if n.startswith("fotos/") and not n.endswith("/")}
        musica = z.read("musica.mp3") if "musica.mp3" in z.namelist() else None
    nuevo_estado(config, fotos, musica)

# ------------------------------------------------------------------ barra lateral
with st.sidebar:
    st.markdown("## 💌 Estudio de invitaciones")
    st.caption(f"Proyecto: **{c['novios'].get('texto') or c['novios']['nombre1'] + ' & ' + c['novios']['nombre2']}**")
    st.divider()
    st.markdown("**Proyecto**")
    col1, col2 = st.columns(2)
    if col1.button("Nuevo", use_container_width=True):
        nuevo_estado(build.config_vacia()); st.rerun()
    if col2.button("Ejemplo", use_container_width=True, help="Carga un ejemplo con datos ficticios como punto de partida"):
        nuevo_estado(build.config_ejemplo()); st.rerun()
    up = st.file_uploader("Abrir proyecto (.zip)", type=["zip"], key=k("abrir"))
    if up is not None and ss.get("ultimo_abierto") != up.file_id:
        ss.ultimo_abierto = up.file_id
        try:
            abrir_proyecto(up.getvalue()); st.rerun()
        except Exception as e:
            st.error(f"No pude abrir ese archivo: {e}")
    if st.button("💾 Guardar proyecto", use_container_width=True, help="Guarda datos, fotos y música para volver a editar después"):
        ss.proyecto_zip = proyecto_zip()
    if ss.get("proyecto_zip"):
        st.download_button("⬇️ Descargar proyecto (.zip)", ss.proyecto_zip, file_name=f"proyecto-{c.get('slug', 'invitacion')}.zip",
                           mime="application/zip", use_container_width=True, on_click=lambda: ss.pop("proyecto_zip", None))
    st.divider()
    st.caption("Tip: guarda el proyecto antes de cerrar la página; Streamlit no conserva los archivos entre sesiones.")

st.title("Estudio de invitaciones")
tabs = st.tabs(["📝 Datos", "📍 Lugar e itinerario", "🎁 Detalles", "📷 Fotos", "🎵 Música",
                "🎨 Diseño", "✍️ Textos", "👀 Vista previa y descarga", "👥 Invitados"])

# ------------------------------------------------------------------ 1. datos
with tabs[0]:
    st.subheader("Los novios")
    a, b_, m = st.columns([2, 2, 1])
    c["novios"]["nombre1"] = a.text_input("Nombre 1", c["novios"]["nombre1"], key=k("n1"))
    c["novios"]["nombre2"] = b_.text_input("Nombre 2", c["novios"]["nombre2"], key=k("n2"))
    c["novios"]["monograma"] = m.text_input("Monograma", c["novios"].get("monograma", ""), key=k("mono"),
                                            help="Va en el sello y en el ícono. Vacío = iniciales")
    auto = f"{c['novios']['nombre1'].strip()} & {c['novios']['nombre2'].strip()}"
    c["novios"]["texto"] = st.text_input("Cómo se escriben juntos", c["novios"].get("texto") or auto, key=k("ntexto"))

    st.subheader("Fecha y hora")
    a, b_, d_, z_ = st.columns(4)
    c["fecha"] = a.date_input("Fecha del evento", date.fromisoformat(str(c["fecha"])), key=k("fecha"), format="DD/MM/YYYY").isoformat()
    c["hora_inicio"] = b_.time_input("Hora de inicio", time.fromisoformat(str(c["hora_inicio"])), key=k("hi"), step=900).strftime("%H:%M")
    c["hora_fin"] = d_.time_input("Hora de fin", time.fromisoformat(str(c["hora_fin"])), key=k("hf"), step=900).strftime("%H:%M")
    zonas = list(build.ZONAS)
    actual = next((z for z, v in build.ZONAS.items() if v == c.get("zona", "-06:00")), zonas[0])
    c["zona"] = build.ZONAS[z_.selectbox("Zona horaria", zonas, index=zonas.index(actual), key=k("zona"))]

    a, b_, d_ = st.columns(3)
    c["ciudad"] = a.text_input("Ciudad (para el pie de página)", c.get("ciudad", ""), key=k("ciudad"))
    c["hashtag"] = b_.text_input("Hashtag (opcional)", c.get("hashtag", ""), key=k("hashtag"))
    lim = c.get("fecha_limite")
    usar_lim = d_.checkbox("Fecha límite para confirmar", bool(lim), key=k("usarlim"))
    if usar_lim:
        c["fecha_limite"] = d_.date_input("Confirmar antes del", date.fromisoformat(lim) if lim else date.fromisoformat(c["fecha"]),
                                         key=k("lim"), format="DD/MM/YYYY").isoformat()
    else:
        c["fecha_limite"] = ""

    st.subheader("Publicación")
    a, b_ = st.columns(2)
    c["slug"] = build.slugify(a.text_input("Nombre corto del proyecto", c.get("slug", ""), key=k("slug"),
                                           help="Úsalo también como nombre del proyecto en Cloudflare"))
    c["site_url"] = b_.text_input("Enlace final de la invitación", c.get("site_url", "") or f"https://{c['slug']}.pages.dev/",
                                  key=k("site"), help="Sirve para la vista previa de WhatsApp y los enlaces de invitados")

    st.subheader("Padres y padrinos (opcional)")
    c["secciones"]["padres"] = st.toggle("Mostrar padres y padrinos", c["secciones"].get("padres", False), key=k("spadres"))
    if c["secciones"]["padres"]:
        df = pd.DataFrame(c.get("familia") or [{"grupo": "Padres de la novia", "nombres": ""}])
        ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=k("familia"),
                            column_config={"grupo": "Grupo (ej. Padres del novio, Padrinos de anillos)",
                                           "nombres": "Nombres (sepáralos con punto y coma ;)"})
        c["familia"] = [{kk: ("" if pd.isna(v) else str(v)) for kk, v in r.items()} for r in ed.to_dict("records") if str(r.get("grupo") or "").strip()]
        a, b_ = st.columns(2)
        c["textos"]["padres_eyebrow"] = a.text_input("Texto pequeño", c["textos"]["padres_eyebrow"], key=k("pey"))
        c["textos"]["padres_titulo"] = b_.text_input("Título", c["textos"]["padres_titulo"], key=k("pti"))

    st.subheader("Frase (opcional)")
    c["secciones"]["frase"] = st.toggle("Mostrar frase", c["secciones"]["frase"], key=k("sfrase"))
    if c["secciones"]["frase"]:
        a, b_ = st.columns([3, 1])
        c["frase"]["texto"] = a.text_area("Frase", c["frase"]["texto"], key=k("frase"), height=80)
        c["frase"]["autor"] = b_.text_input("Autor", c["frase"]["autor"], key=k("autor"))

# ------------------------------------------------------------------ 2. lugar e itinerario
with tabs[1]:
    c["secciones"]["lugar"] = st.toggle("Mostrar sección del lugar", c["secciones"]["lugar"], key=k("slugar"))
    st.caption("Una fila por lugar. Si la ceremonia y la recepción son en sitios distintos, agrega dos filas.")
    df = pd.DataFrame(c["lugares"] or [{"titulo": "El lugar", "subtitulo": "", "hora": "", "nombre": "", "direccion": "", "mapa": ""}])
    ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=k("lugares"),
                        column_config={"titulo": "Título", "subtitulo": "Subtítulo", "hora": "Hora (opcional)",
                                       "nombre": "Nombre del lugar", "direccion": "Dirección",
                                       "mapa": st.column_config.LinkColumn("Enlace de Google Maps")})
    c["lugares"] = [{kk: ("" if pd.isna(v) else str(v)) for kk, v in r.items()} for r in ed.to_dict("records") if str(r.get("nombre") or "").strip()]

    st.divider()
    c["secciones"]["itinerario"] = st.toggle("Mostrar itinerario", c["secciones"]["itinerario"], key=k("sitin"))
    df = pd.DataFrame(c["itinerario"] or [{"hora": "", "titulo": "", "descripcion": "", "icono": "anillos"}])
    ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=k("itin"),
                        column_config={"hora": "Hora", "titulo": "Momento", "descripcion": "Frase corta",
                                       "icono": st.column_config.SelectboxColumn("Ícono", options=ICONOS, required=True)})
    c["itinerario"] = [{kk: ("" if pd.isna(v) else str(v)) for kk, v in r.items()} for r in ed.to_dict("records") if str(r.get("titulo") or "").strip()]
    st.caption("Íconos: " + ", ".join(ICONOS) + ".")

    st.divider()
    c["secciones"]["hospedaje"] = st.toggle("Mostrar hospedaje sugerido", c["secciones"].get("hospedaje", False), key=k("shosp"))
    if c["secciones"]["hospedaje"]:
        df = pd.DataFrame(c.get("hospedaje") or [{"nombre": "", "detalle": "", "codigo": "", "telefono": "", "enlace": ""}])
        ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=k("hosp"),
                            column_config={"nombre": "Hotel", "detalle": "Detalle", "codigo": "Código de descuento",
                                           "telefono": "Teléfono", "enlace": st.column_config.LinkColumn("Enlace para reservar")})
        c["hospedaje"] = [{kk: ("" if pd.isna(v) else str(v)) for kk, v in r.items()} for r in ed.to_dict("records") if str(r.get("nombre") or "").strip()]
        a, b_, d_ = st.columns(3)
        c["textos"]["hospedaje_eyebrow"] = a.text_input("Texto pequeño", c["textos"]["hospedaje_eyebrow"], key=k("hey"))
        c["textos"]["hospedaje_titulo"] = b_.text_input("Título", c["textos"]["hospedaje_titulo"], key=k("hti"))
        c["textos"]["hospedaje_nota"] = d_.text_input("Nota", c["textos"]["hospedaje_nota"], key=k("hno"))

# ------------------------------------------------------------------ 3. detalles
with tabs[2]:
    st.subheader("Código de vestimenta")
    c["secciones"]["vestimenta"] = st.toggle("Mostrar código de vestimenta", c["secciones"]["vestimenta"], key=k("svest"))
    if c["secciones"]["vestimenta"]:
        a, b_, d_ = st.columns(3)
        c["vestimenta"]["codigo"] = a.text_input("Código", c["vestimenta"]["codigo"], key=k("vcod"))
        c["vestimenta"]["etiqueta_traje"] = b_.text_input("Etiqueta del traje", c["vestimenta"]["etiqueta_traje"], key=k("vtraje"))
        c["vestimenta"]["etiqueta_vestido"] = d_.text_input("Etiqueta del vestido", c["vestimenta"]["etiqueta_vestido"], key=k("vvest"))
        c["vestimenta"]["mostrar_figuras"] = st.checkbox("Mostrar ilustraciones de traje y vestido", c["vestimenta"]["mostrar_figuras"], key=k("vfig"))
        c["vestimenta"]["nota"] = st.text_input("Nota (opcional)", c["vestimenta"]["nota"], key=k("vnota"))
    c["secciones"]["sin_ninos"] = st.toggle("Aviso de evento sin niños", c["secciones"]["sin_ninos"], key=k("sninos"))
    if c["secciones"]["sin_ninos"]:
        a, b_ = st.columns([1, 3])
        c["textos"]["sin_ninos_titulo"] = a.text_input("Título del aviso", c["textos"]["sin_ninos_titulo"], key=k("ninot"))
        c["textos"]["sin_ninos_nota"] = b_.text_input("Texto", c["textos"]["sin_ninos_nota"], key=k("ninon"))

    st.divider()
    st.subheader("Mesa de regalos")
    c["secciones"]["regalos"] = st.toggle("Mostrar mesa de regalos", c["secciones"]["regalos"], key=k("sreg"))
    df = pd.DataFrame(c["regalos"] or [{"tienda": "", "etiqueta": "Número de evento", "numero": "", "enlace": "", "boton": "", "nota": ""}])
    ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=k("regalos"),
                        column_config={"tienda": "Tienda o forma", "etiqueta": "Etiqueta del número", "numero": "Número",
                                       "enlace": st.column_config.LinkColumn("Enlace"), "boton": "Texto del botón",
                                       "nota": "Nota (ej. lluvia de sobres)"})
    c["regalos"] = [{kk: ("" if pd.isna(v) else str(v)) for kk, v in r.items()} for r in ed.to_dict("records") if str(r.get("tienda") or "").strip()]

    st.divider()
    st.subheader("Confirmación por WhatsApp")
    c["secciones"]["confirmacion"] = st.toggle("Mostrar confirmación", c["secciones"]["confirmacion"], key=k("srsvp"))
    df = pd.DataFrame(c["contactos"] or [{"nombre": "", "telefono": ""}])
    ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=k("contactos"),
                        column_config={"nombre": "Nombre", "telefono": "Teléfono a 10 dígitos"})
    c["contactos"] = [{"nombre": ("" if pd.isna(r["nombre"]) else str(r["nombre"])), "telefono": "".join(ch for ch in str(r["telefono"]) if ch.isdigit())}
                      for r in ed.to_dict("records") if str(r.get("telefono") or "").strip() not in ("", "nan")]
    malos = [p["telefono"] for p in c["contactos"] if len(p["telefono"]) != 10]
    if malos:
        st.warning(f"Revisa estos teléfonos, deben tener 10 dígitos: {', '.join(malos)}")
    c["textos"]["evento_de"] = st.text_input("En el mensaje de WhatsApp: «Confirmo mi asistencia a …»", c["textos"]["evento_de"], key=k("evde"),
                                             help="Ej. «la boda de», «los XV años de», «la celebración de»")

# ------------------------------------------------------------------ 4. fotos
with tabs[3]:
    st.caption("Sube las fotos en la mejor calidad posible. Marca cuál va en la portada y cuál en la vista previa de WhatsApp; "
               "las demás forman la galería en el orden en que aparecen aquí (dos verticales y una horizontal).")
    subidas = st.file_uploader("Agregar fotos", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, key=k("subir_fotos"))
    for f in subidas or []:
        data = f.getvalue()
        fid = hashlib.sha1(data).hexdigest()[:12] + ".jpg"
        if fid not in ss.fotos and fid not in ss.setdefault("quitadas", set()):
            ss.fotos[fid] = data
            c["fotos"].append({"id": fid, "nombre": f.name, "fx": 0.5, "fy": 0.5, "zoom": 1.0, "zoom_portada": 1.0,
                               "zoom_previa": 1.0, "portada": not c["fotos"], "vista_previa": False, "galeria": bool(c["fotos"])})
    c["fotos"] = [f for f in c["fotos"] if f["id"] in ss.fotos]
    if not c["fotos"]:
        st.info("Aún no hay fotos. Sin fotos, la portada y la galería muestran recuadros de ejemplo.")
    else:
        ids = [f["id"] for f in c["fotos"]]
        nombres_f = {f["id"]: f"{i + 1}. {f.get('nombre', f['id'])}" for i, f in enumerate(c["fotos"])}
        actual_p = next((f["id"] for f in c["fotos"] if f.get("portada")), ids[0])
        actual_v = next((f["id"] for f in c["fotos"] if f.get("vista_previa")), actual_p)
        a, b_ = st.columns(2)
        sel_p = a.selectbox("Foto de portada", ids, index=ids.index(actual_p), format_func=nombres_f.get, key=k("selport"))
        sel_v = b_.selectbox("Foto para la vista previa de WhatsApp", ids, index=ids.index(actual_v), format_func=nombres_f.get, key=k("selprev"))
        for f in c["fotos"]:
            f["portada"] = f["id"] == sel_p
            f["vista_previa"] = f["id"] == sel_v
    gal_i = 0
    for idx, f in enumerate(list(c["fotos"])):
        en_gal = f.get("galeria", True)
        horizontal = build.tile_es_horizontal(gal_i) if en_gal else False
        with st.container(border=True):
            col_img, col_ctrl = st.columns([2, 3])
            im = build.abrir(ss.fotos[f["id"]])
            with col_ctrl:
                st.markdown(f"**{idx + 1}. {f.get('nombre', f['id'])}**" + (f" · galería #{gal_i + 1} ({'horizontal' if horizontal else 'vertical'})" if en_gal else ""))
                a, b_, d_ = st.columns(3)
                f["fx"] = a.slider("Centro horizontal", 0.0, 1.0, float(f["fx"]), 0.01, key=k(f"fx{f['id']}"))
                f["fy"] = b_.slider("Centro vertical", 0.0, 1.0, float(f["fy"]), 0.01, key=k(f"fy{f['id']}"))
                f["zoom"] = d_.slider("Acercar (galería)", 1.0, 2.5, float(f.get("zoom", 1.0)), 0.05, key=k(f"z{f['id']}"))
                f["galeria"] = st.checkbox("Incluir en la galería", en_gal, key=k(f"g{f['id']}"))
                if f["portada"]:
                    f["zoom_portada"] = st.slider("Acercar (portada)", 1.0, 2.5, float(f.get("zoom_portada", 1.0)), 0.05, key=k(f"zp{f['id']}"))
                if f["vista_previa"]:
                    f["zoom_previa"] = st.slider("Acercar (vista previa)", 1.0, 2.5, float(f.get("zoom_previa", 1.0)), 0.05, key=k(f"zv{f['id']}"))
                a, b_, d_ = st.columns(3)
                if a.button("⬆️ Subir", key=k(f"up{f['id']}"), disabled=idx == 0):
                    c["fotos"][idx - 1], c["fotos"][idx] = c["fotos"][idx], c["fotos"][idx - 1]; st.rerun()
                if b_.button("⬇️ Bajar", key=k(f"dn{f['id']}"), disabled=idx == len(c["fotos"]) - 1):
                    c["fotos"][idx + 1], c["fotos"][idx] = c["fotos"][idx], c["fotos"][idx + 1]; st.rerun()
                if d_.button("🗑️ Quitar", key=k(f"del{f['id']}")):
                    c["fotos"].pop(idx); ss.fotos.pop(f["id"], None); ss.setdefault("quitadas", set()).add(f["id"]); st.rerun()
            with col_img:
                vistas = []
                if en_gal:
                    vistas.append(("Galería", build.recorte(im, 16 / 10 if horizontal else 3 / 4, f["fx"], f["fy"], f["zoom"])))
                if f.get("portada"):
                    vistas.append(("Portada", build.recorte(im, 9 / 16, f["fx"], f["fy"], f.get("zoom_portada", 1.0))))
                if f.get("vista_previa"):
                    vistas.append(("WhatsApp", build.recorte(im, 1200 / 630, f["fx"], f["fy"], f.get("zoom_previa", 1.0))))
                if not vistas:
                    vistas.append(("Original", im))
                cols = st.columns(len(vistas))
                for col, (t, v) in zip(cols, vistas):
                    v = v.copy(); v.thumbnail((360, 360))
                    col.image(v, caption=t, width=150)
        if en_gal:
            gal_i += 1

# ------------------------------------------------------------------ 5. música
with tabs[4]:
    c["musica"]["activa"] = st.toggle("La invitación tiene música", c["musica"]["activa"], key=k("mact"))
    if c["musica"]["activa"]:
        m = st.file_uploader("Canción (mp3, m4a, wav)", type=["mp3", "m4a", "wav", "aac", "ogg"], key=k("msubir"))
        if m is not None and ss.get("ultima_cancion") != m.file_id:
            with st.spinner("Comprimiendo la canción para que cargue rápido…"):
                ss.musica = build.comprimir_musica(m.getvalue())
            ss.ultima_cancion = m.file_id
            c["musica"]["nombre"] = m.name
        if ss.musica:
            st.success(f"Canción lista: {c['musica'].get('nombre') or 'musica.mp3'} · {len(ss.musica) / 1e6:.1f} MB")
            st.audio(ss.musica, format="audio/mp3", start_time=int(c["musica"].get("inicio", 0)))
            a, b_ = st.columns(2)
            c["musica"]["inicio"] = a.number_input("Empezar en el segundo", 0, 600, int(c["musica"].get("inicio", 0)), key=k("minicio"))
            c["musica"]["volumen"] = b_.slider("Volumen", 0.1, 1.0, float(c["musica"].get("volumen", 0.7)), 0.05, key=k("mvol"))
            if st.button("Quitar canción"):
                ss.musica = None; st.rerun()
        else:
            st.info("Sube la canción. Suena cuando el invitado toca el sello del sobre.")

# ------------------------------------------------------------------ 6. diseño
with tabs[5]:
    st.subheader("Estilo base")
    estilos = list(build.ESTILOS)
    a, b_ = st.columns([2, 1])
    c["diseno"]["estilo"] = a.selectbox("Estilo", estilos, index=estilos.index(c["diseno"].get("estilo", "clasico")),
                                        format_func=lambda e: build.ESTILOS[e]["nombre"], key=k("estilo"),
                                        help="Cambia adornos, fondos y formas de la invitación")
    b_.write(""); b_.write("")
    if b_.button("✨ Usar colores, letras y efectos recomendados", use_container_width=True):
        e = build.ESTILOS[c["diseno"]["estilo"]]
        c["diseno"].update(paleta=e["paleta"], fuente_script=e["fuente_script"], fuente_serif=e["fuente_serif"],
                           fuente_sans=e["fuente_sans"], sello=e["sello"], **build.PALETAS[e["paleta"]])
        c["efectos"].update(e["efectos"])
        ss.rev += 1; st.rerun()

    st.subheader("Paleta de colores")
    nombres = list(build.PALETAS) + ["Personalizada"]
    actual = c["diseno"].get("paleta", "Gris azulado")
    a, b_ = st.columns([1, 2])
    pal = a.selectbox("Paleta", nombres, index=nombres.index(actual) if actual in nombres else 0, key=k("paleta"))
    c["diseno"]["paleta"] = pal
    if pal == "Personalizada":
        c["diseno"]["tono"] = a.slider("Tono", 0, 359, int(c["diseno"].get("tono", 210)), key=k("tono"))
        c["diseno"]["saturacion"] = a.slider("Intensidad del color", 0.0, 2.5, float(c["diseno"].get("saturacion", 1.0)), 0.05, key=k("sat"))
    else:
        c["diseno"]["tono"] = build.PALETAS[pal]["tono"]
        c["diseno"]["saturacion"] = build.PALETAS[pal]["saturacion"]
    chip = lambda col, sz=40: f'<span style="display:inline-block;width:{sz}px;height:{sz}px;border-radius:50%;margin-right:7px;background:{col};border:1px solid #8884"></span>'
    b_.markdown("<div style='margin-top:1.8rem'>" + "".join(chip(col) for col in build.muestra_paleta(c["diseno"]["tono"], c["diseno"]["saturacion"])) + "</div>",
                unsafe_allow_html=True)
    with st.expander("Ver todas las paletas"):
        filas = "".join(f"<div style='margin:4px 0'><span style='display:inline-block;width:130px'>{n}</span>"
                        + "".join(chip(col, 22) for col in build.muestra_paleta(v["tono"], v["saturacion"])) + "</div>"
                        for n, v in build.PALETAS.items())
        st.markdown(filas, unsafe_allow_html=True)

    sellos = list(build.SELLOS)
    c["diseno"]["sello"] = st.selectbox("Color de la cera del sello", sellos, index=sellos.index(c["diseno"].get("sello", "negro")),
                                        format_func=str.capitalize, key=k("sello"))

    st.subheader("Tipografía")
    a, b_, d_ = st.columns(3)
    fs = list(build.FUENTES_SCRIPT); fse = list(build.FUENTES_SERIF); fsa = list(build.FUENTES_SANS)
    c["diseno"]["fuente_script"] = a.selectbox("Letra manuscrita (nombres y títulos)", fs, index=fs.index(c["diseno"]["fuente_script"]), key=k("fscript"))
    c["diseno"]["fuente_serif"] = b_.selectbox("Letra de texto", fse, index=fse.index(c["diseno"]["fuente_serif"]), key=k("fserif"))
    c["diseno"]["fuente_sans"] = d_.selectbox("Letra de etiquetas", fsa, index=fsa.index(c["diseno"]["fuente_sans"]), key=k("fsans"))
    fuentes_css = build.url_fuentes(c["diseno"]["fuente_serif"], c["diseno"]["fuente_script"], c["diseno"]["fuente_sans"])
    st.markdown(f"""<link href="{fuentes_css}" rel="stylesheet">
<div style="padding:14px 18px;border:1px solid #8883;border-radius:10px;text-align:center">
<div style="font-family:'{c["diseno"]["fuente_sans"]}';letter-spacing:.3em;font-size:.7rem;text-transform:uppercase;opacity:.7">{c["textos"]["hero_kicker"]}</div>
<div style="font-family:'{c["diseno"]["fuente_script"]}';font-size:2.6rem;line-height:1.3">{c["novios"].get("texto") or "Sofía &amp; Mateo"}</div>
<div style="font-family:'{c["diseno"]["fuente_serif"]}';font-size:1.1rem;font-style:italic">Nos encantará compartir este día con ustedes</div></div>""",
                unsafe_allow_html=True)

    st.subheader("Efectos")
    a, b_, d_ = st.columns(3)
    ef = c["efectos"]
    opts = list(build.EFECTOS_FONDO)
    ef["fondo"] = a.selectbox("Fondo animado", opts, index=opts.index(ef.get("fondo", "petalos")), format_func=build.EFECTOS_FONDO.get, key=k("efondo"))
    opts = list(build.EFECTOS_APERTURA)
    ef["apertura"] = b_.selectbox("Al abrir el sobre", opts, index=opts.index(ef.get("apertura", "petalos")), format_func=build.EFECTOS_APERTURA.get, key=k("eaper"))
    opts = list(build.EFECTOS_FINAL)
    ef["final"] = d_.selectbox("Gran final (al llegar al final)", opts, index=opts.index(ef.get("final", "fuegos")), format_func=build.EFECTOS_FINAL.get, key=k("efinal"))
    a, b_, d_ = st.columns(3)
    ef["toque"] = a.toggle("Estela de destellos al tocar", ef.get("toque", False), key=k("etoque"))
    c["funciones"]["sobre3d"] = b_.toggle("Sobre 3D", c["funciones"]["sobre3d"], key=k("f3d"), help="Apagado = sobre animado clásico")
    c["funciones"]["sonido_fuegos"] = d_.toggle("Sonido de fuegos artificiales", c["funciones"].get("sonido_fuegos", True), key=k("fson"),
                                                disabled=ef["final"] != "fuegos")
    c["funciones"]["petalos"] = ef["fondo"] == "petalos"
    c["funciones"]["fuegos"] = ef["final"] == "fuegos"

    st.subheader("Secciones")
    a, b_ = st.columns(2)
    c["secciones"]["cuenta_regresiva"] = a.toggle("Cuenta regresiva y botones de calendario", c["secciones"]["cuenta_regresiva"], key=k("scuenta"))
    c["secciones"]["galeria"] = b_.toggle("Galería de fotos", c["secciones"]["galeria"], key=k("sgal"))
    st.caption("Las demás secciones se activan o quitan en su propia pestaña.")

# ------------------------------------------------------------------ 7. textos
with tabs[6]:
    st.caption("Todos los textos de la invitación. Cambia solo los que quieras.")
    etiquetas = {
        "titulo_evento": "Título del evento (calendario)", "og_descripcion": "Texto de la vista previa en WhatsApp",
        "intro": "Sobre: texto de arriba", "toque": "Sobre: indicación", "hero_kicker": "Portada: «Nos casamos»",
        "pase_para": "Pase: «Invitación para»", "pase_reservado": "Pase: «Hemos reservado»",
        "pase_singular": "Pase: 1 lugar", "pase_plural": "Pase: varios lugares",
        "cuenta_regresiva": "Cuenta regresiva", "guarden_fecha": "Botones de calendario",
        "lugar_eyebrow": "Lugar: texto pequeño", "lugar_titulo": "Lugar: título", "como_llegar": "Botón del mapa",
        "itinerario_eyebrow": "Itinerario: texto pequeño", "itinerario_titulo": "Itinerario: título",
        "vestimenta_eyebrow": "Vestimenta: texto pequeño", "galeria_eyebrow": "Galería: texto pequeño",
        "galeria_titulo": "Galería: título", "regalos_eyebrow": "Regalos: texto pequeño", "regalos_titulo": "Regalos: título",
        "regalos_nota": "Regalos: texto", "copiar": "Botón copiar", "copiado": "Botón al copiar", "copiado_aviso": "Aviso al copiar",
        "rsvp_eyebrow": "Confirmación: texto pequeño", "rsvp_titulo": "Confirmación: título", "rsvp_texto": "Confirmación: texto",
        "limite_titulo": "Fecha límite: etiqueta", "confirmar": "Botón de WhatsApp", "gracias": "Pie: agradecimiento", "firma": "Pie: firma",
    }
    cols = st.columns(2)
    for i, (clave, nombre) in enumerate(etiquetas.items()):
        c["textos"][clave] = cols[i % 2].text_input(nombre, c["textos"].get(clave, ""), key=k(f"t{clave}"))

# ------------------------------------------------------------------ 8. vista previa y descarga
with tabs[7]:
    a, b_ = st.columns([1, 1])
    with a:
        st.subheader("Vista previa")
        con_musica = st.checkbox("Incluir música en la vista previa", False, help="Hace la vista previa más pesada")
        if st.button("🔄 Generar vista previa", type="primary"):
            with st.spinner("Armando la invitación…"):
                arch = build.construir(c, ss.fotos, ss.musica, ligero=True)
                ss.preview_html = build.vista_previa(arch, con_musica)
        if ss.get("preview_html"):
            components.html(ss.preview_html, height=780, scrolling=True)
            st.caption("Toca el sello para abrir. La vista previa usa fotos más ligeras; el .zip final va en calidad completa.")
    with b_:
        st.subheader("Descargar para publicar")
        problemas = []
        if not c["novios"]["nombre1"].strip() or not c["novios"]["nombre2"].strip():
            problemas.append("Faltan los nombres.")
        if c["secciones"]["confirmacion"] and not c["contactos"]:
            problemas.append("La confirmación está activa pero no hay teléfonos.")
        if c["musica"]["activa"] and not ss.musica:
            problemas.append("La música está activa pero no hay canción (se publicará sin música).")
        if not c["fotos"]:
            problemas.append("No hay fotos (se verán recuadros de ejemplo).")
        if not c.get("site_url"):
            problemas.append("Falta el enlace final (la vista previa de WhatsApp no mostrará foto).")
        for p in problemas:
            st.warning(p)
        if st.button("📦 Preparar .zip final"):
            with st.spinner("Generando archivos en calidad completa…"):
                arch = build.construir(c, ss.fotos, ss.musica)
                ss.zip_final = build.a_zip(arch)
                ss.zip_info = (len(arch), sum(len(v) for v in arch.values()))
        if ss.get("zip_final"):
            n, peso = ss.zip_info
            st.success(f"Listo: {n} archivos · {peso / 1e6:.1f} MB")
            st.download_button("⬇️ Descargar invitación (.zip)", ss.zip_final, file_name=f"{c['slug']}.zip", mime="application/zip", type="primary")
        st.divider()
        st.subheader("🚀 Publicar directo en Cloudflare")
        try:
            cf_sec = st.secrets.get("cloudflare", {})
            cf_cuenta_def, cf_token_def = cf_sec.get("account_id", ""), cf_sec.get("api_token", "")
        except Exception:
            cf_cuenta_def, cf_token_def = "", ""
        with st.expander("Datos de tu cuenta de Cloudflare", expanded=not (cf_cuenta_def and cf_token_def)):
            ss.cf_cuenta = st.text_input("ID de cuenta", ss.get("cf_cuenta", cf_cuenta_def),
                                         help="Es el código largo en la dirección del panel: dash.cloudflare.com/<ID>/…")
            ss.cf_token = st.text_input("Token de API (permiso Cloudflare Pages: Edit)", ss.get("cf_token", cf_token_def), type="password")
            st.caption("Para no escribirlos cada vez, guárdalos en los *Secrets* de Streamlit Cloud: "
                       "`[cloudflare]` con `account_id` y `api_token`.")
        st.caption(f"Se publicará en el proyecto **{c['slug']}** (si no existe, se crea).")
        if st.button("🚀 Publicar ahora", type="primary", disabled=not (ss.get("cf_cuenta") and ss.get("cf_token"))):
            from motor import cloudflare
            barra = st.progress(0.0, "Generando archivos…")
            try:
                arch = build.construir(c, ss.fotos, ss.musica)
                url, url_dep = cloudflare.publicar(ss.cf_cuenta.strip(), ss.cf_token.strip(), c["slug"], arch,
                                                   avance=lambda m, f: barra.progress(min(1.0, f), m))
                st.success(f"¡Publicada! {url}")
                if url_dep:
                    st.caption(f"Versión de esta publicación: {url_dep}")
                if c.get("site_url", "").rstrip("/") != url.rstrip("/"):
                    st.info("El enlace final es distinto al de la pestaña Datos. Actualízalo allí y vuelve a publicar "
                            "para que la vista previa de WhatsApp y los enlaces de invitados usen el correcto.")
            except Exception as e:
                st.error(f"No se pudo publicar: {e}")
        st.markdown(f"""
**O publícala a mano en Cloudflare Pages**
1. Descomprime el .zip.
2. Cloudflare → **Workers & Pages** → **Create** → pestaña **Pages** → **Upload assets**.
3. Nombre del proyecto: `{c['slug']}` → **Create project** → arrastra la carpeta → **Deploy site**.
4. Para actualizar: abre el proyecto → **Create deployment** → arrastra la carpeta nueva.

El enlace queda como `https://{c['slug']}.pages.dev`. Si Cloudflare te da otro, ponlo en **Datos → Enlace final** y vuelve a generar.
""")

# ------------------------------------------------------------------ 9. invitados
with tabs[8]:
    st.caption("Crea un enlace personalizado por familia: al abrirlo, la invitación muestra su nombre y sus lugares, "
               "y el mensaje de confirmación por WhatsApp ya lleva su nombre.")
    if not c.get("site_url"):
        st.warning("Primero escribe el enlace final en la pestaña Datos.")
    arch_inv = st.file_uploader("Lista en Excel o CSV (columnas: Nombre, Pases)", type=["xlsx", "csv"], key=k("lista"))
    if arch_inv is not None:
        try:
            dfl = pd.read_csv(arch_inv) if arch_inv.name.endswith(".csv") else pd.read_excel(arch_inv)
            cols_l = {col.lower().strip(): col for col in dfl.columns}
            n_col = cols_l.get("nombre") or dfl.columns[0]
            p_col = cols_l.get("pases") or (dfl.columns[1] if len(dfl.columns) > 1 else None)
            ss.invitados = pd.DataFrame({"Nombre": dfl[n_col], "Pases": dfl[p_col] if p_col else ""})
        except Exception as e:
            st.error(f"No pude leer la lista: {e}")
    base = ss.get("invitados", pd.DataFrame({"Nombre": ["Familia Pérez"], "Pases": [4]}))
    inv = st.data_editor(base, num_rows="dynamic", use_container_width=True, key=k("inv"))
    plantilla_msg = st.text_area("Mensaje para enviar (usa {nombre}, {pases} y {enlace})",
                                 "¡Hola, {nombre}! 💌 Con mucho cariño les compartimos nuestra invitación: {enlace}", key=k("msg"))
    if c.get("site_url"):
        filas = build.enlaces_invitados(c["site_url"], list(zip(inv["Nombre"].fillna(""), inv["Pases"].fillna(""))))
        for f in filas:
            f["mensaje"] = plantilla_msg.format(nombre=f["nombre"], pases=f["pases"], enlace=f["enlace"])
        res = pd.DataFrame(filas)
        if not res.empty:
            st.dataframe(res, use_container_width=True, column_config={"enlace": st.column_config.LinkColumn("Enlace")})
            buf = io.BytesIO(); res.to_excel(buf, index=False)
            st.download_button("⬇️ Descargar enlaces (Excel)", buf.getvalue(), file_name=f"invitados-{c['slug']}.xlsx")
