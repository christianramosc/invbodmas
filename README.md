# Estudio de invitaciones

Editor en Streamlit para crear invitaciones digitales de lujo (sobre 3D que se abre, música, pétalos,
fuegos artificiales, galería, itinerario, mesa de regalos y confirmación por WhatsApp) a partir de una plantilla.

## Qué hace
1. **Datos, lugar, itinerario, detalles y textos**: todo lo que cambia entre eventos se captura en formularios.
2. **Fotos**: subes las fotos, eliges portada y vista previa de WhatsApp, y ajustas el encuadre de cada una.
   La app las recorta y comprime.
3. **Música**: subes la canción; se comprime a 128 kbps (requiere `ffmpeg`, incluido en `packages.txt`).
4. **Diseño**:
   - 4 estilos base: clásico elegante, playa, rústico y moderno minimalista (cada uno sugiere colores, letras y efectos).
   - 20 paletas (o una personalizada) y 5 colores de cera para el sello.
   - 9 letras manuscritas, 8 de texto y 7 de etiquetas.
   - Efectos: fondo animado (pétalos, corazones, luciérnagas, destellos, nieve, hojas, burbujas, confeti),
     efecto al abrir el sobre, gran final (fuegos artificiales con sonido, cañones de confeti, linternas
     flotantes, lluvia de corazones, destellos) y estela de destellos al tocar.
   - Secciones opcionales: frase, padres y padrinos, cuenta regresiva, lugar(es), itinerario con 14 íconos,
     hospedaje, vestimenta, aviso sin niños, galería, mesa de regalos y confirmación por WhatsApp.
5. **Vista previa** dentro de la app, **descarga del .zip** y **publicación directa en Cloudflare Pages**
   (con el ID de cuenta y un token de API con permiso «Cloudflare Pages: Edit»).
6. **Invitados**: subes un Excel (Nombre, Pases) y obtienes el enlace personalizado de cada familia
   y el mensaje para enviarlo.
7. **Proyectos**: “Guardar proyecto” descarga un .zip con datos, fotos y música; “Abrir proyecto” lo recupera.

## Estructura
```
app.py                 editor (Streamlit)
motor/build.py         genera la invitación: estilos, paletas, fotos, música, zip, vista previa, enlaces
motor/cloudflare.py    publicación directa en Cloudflare Pages
motor/fuentes/         letras manuscritas (licencia SIL OFL) para el ícono con monograma
plantilla/index.html.j2  la invitación (Jinja2)
plantilla/js/          sobre 3D (three.min.js + sobre3d.js) y efectos (efectos.js)
plantilla/iconos.json  íconos del itinerario
ejemplos/              configuración de ejemplo con datos ficticios (Sofía & Mateo, sin fotos)
```

## Ejecutar en tu computadora
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publicar la app en Streamlit Community Cloud
1. Sube este repositorio a GitHub.
2. En share.streamlit.io → **Create app** → elige el repo, rama `main` y archivo `app.py`.
3. Recomendado: en **Settings → Sharing**, deja la app privada o protégela, porque es tu herramienta de trabajo.

## Guardar tus datos de Cloudflare
En Streamlit Cloud → tu app → **Settings → Secrets**:
```toml
[cloudflare]
account_id = "tu-id-de-cuenta"
api_token = "tu-token"
```

## Cómo funcionan las paletas
El diseño base es gris azulado. Cada paleta gira el tono y ajusta la intensidad de todos los colores
del diseño (CSS, SVG y el sobre 3D) sin cambiar su luminosidad, así que el contraste siempre se conserva.

## Notas
- Streamlit Cloud no guarda archivos entre sesiones: guarda cada proyecto con “Guardar proyecto”.
- La vista previa usa fotos ligeras; el .zip final va en calidad completa.
- Para la vista previa de WhatsApp, escribe el **enlace final** (por ejemplo `https://nombre.pages.dev/`) antes de generar el .zip.
