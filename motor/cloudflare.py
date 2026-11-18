"""Publicación directa en Cloudflare Pages (subida directa, igual que hace `wrangler pages deploy`).

Necesita:
- ID de la cuenta de Cloudflare (aparece en la URL del panel: dash.cloudflare.com/<ID>/...).
- Un token de API con el permiso «Cloudflare Pages: Edit»
  (Perfil → API Tokens → Create Token → Custom token → Account · Cloudflare Pages · Edit).
"""
import base64
import json
import mimetypes

import requests
from blake3 import blake3

API = "https://api.cloudflare.com/client/v4"
LIMITE_LOTE = 40 * 1024 * 1024  # bytes en base64 por cada envío


class ErrorCloudflare(Exception):
    pass


def _ok(r):
    try:
        data = r.json()
    except ValueError:
        raise ErrorCloudflare(f"Respuesta inesperada de Cloudflare ({r.status_code}).")
    if not data.get("success", False):
        errs = "; ".join(f'{e.get("code")}: {e.get("message")}' for e in data.get("errors", [])) or r.text[:300]
        raise ErrorCloudflare(errs)
    return data.get("result")


def hash_archivo(ruta, contenido):
    ext = ruta.rsplit(".", 1)[-1] if "." in ruta.rsplit("/", 1)[-1] else ""
    b64 = base64.b64encode(contenido).decode()
    return blake3((b64 + ext).encode()).hexdigest()[:32]


def _tipo(ruta):
    return mimetypes.guess_type(ruta)[0] or "application/octet-stream"


def verificar(cuenta, token):
    """Comprueba que el token funciona. Devuelve los proyectos existentes."""
    r = requests.get(f"{API}/accounts/{cuenta}/pages/projects", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    return [p["name"] for p in (_ok(r) or [])]


def asegurar_proyecto(cuenta, token, nombre):
    h = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API}/accounts/{cuenta}/pages/projects/{nombre}", headers=h, timeout=30)
    if r.status_code == 404:
        r = requests.post(f"{API}/accounts/{cuenta}/pages/projects", headers=h,
                          json={"name": nombre, "production_branch": "main"}, timeout=30)
    return _ok(r)


def publicar(cuenta, token, nombre, archivos, avance=lambda msg, frac: None):
    """archivos: {ruta: bytes}. Devuelve el enlace público del proyecto."""
    h = {"Authorization": f"Bearer {token}"}
    avance("Preparando el proyecto en Cloudflare…", 0.05)
    proyecto = asegurar_proyecto(cuenta, token, nombre)

    avance("Obteniendo permiso de subida…", 0.12)
    jwt = _ok(requests.get(f"{API}/accounts/{cuenta}/pages/projects/{nombre}/upload-token", headers=h, timeout=30))["jwt"]
    hj = {"Authorization": f"Bearer {jwt}"}

    manifest, por_hash = {}, {}
    for ruta, data in archivos.items():
        hh = hash_archivo(ruta, data)
        manifest["/" + ruta.lstrip("/")] = hh
        por_hash[hh] = (ruta, data)

    avance("Revisando qué archivos faltan…", 0.2)
    faltan = _ok(requests.post(f"{API}/pages/assets/check-missing", headers=hj, json={"hashes": list(por_hash)}, timeout=60)) or []

    lotes, actual, peso = [], [], 0
    for hh in faltan:
        ruta, data = por_hash[hh]
        b64 = base64.b64encode(data).decode()
        if actual and peso + len(b64) > LIMITE_LOTE:
            lotes.append(actual); actual, peso = [], 0
        actual.append({"key": hh, "value": b64, "metadata": {"contentType": _tipo(ruta)}, "base64": True})
        peso += len(b64)
    if actual:
        lotes.append(actual)
    for i, lote in enumerate(lotes):
        avance(f"Subiendo archivos ({i + 1}/{len(lotes)})…", 0.25 + 0.55 * (i + 1) / max(1, len(lotes)))
        _ok(requests.post(f"{API}/pages/assets/upload", headers=hj, json=lote, timeout=300))

    avance("Registrando archivos…", 0.85)
    _ok(requests.post(f"{API}/pages/assets/upsert-hashes", headers=hj, json={"hashes": list(por_hash)}, timeout=60))

    avance("Publicando…", 0.92)
    dep = _ok(requests.post(f"{API}/accounts/{cuenta}/pages/projects/{nombre}/deployments", headers=h,
                            files={"manifest": (None, json.dumps(manifest)), "branch": (None, "main")}, timeout=120))
    sub = (proyecto or {}).get("subdomain") or f"{nombre}.pages.dev"
    avance("¡Listo!", 1.0)
    return f"https://{sub}/", (dep or {}).get("url", "")
