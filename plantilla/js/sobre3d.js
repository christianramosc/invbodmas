// Sobre 3D de la invitación (Three.js)
// Si el navegador no tiene WebGL o algo falla, la invitación usa el sobre en CSS.
(function(){
if (!window.THREE3 || !document.getElementById('intro')) { const i = document.getElementById('intro'); i && i.classList.remove('loading3d'); return; }
const { THREE, RoomEnvironment } = window.THREE3;
const INV = window.INV || {};

const intro = document.getElementById('intro');
const reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------- utilidades ----------
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const easeInOut = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const easeOut = t => 1 - Math.pow(1 - t, 3);
const easeIn = t => t * t * t;
const easeOutBack = t => { const c1 = 1.4, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); };
const seg = (t, a, b) => clamp((t - a) / (b - a), 0, 1);
function rng(seed) { return () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }; }

function makeCanvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }

// papel: tono claro con fibras y grano, se tiñe con el color del material
function paperCanvas() {
  const c = makeCanvas(1024, 1024), g = c.getContext('2d'), r = rng(7);
  g.fillStyle = '#e9edf1'; g.fillRect(0, 0, 1024, 1024);
  const img = g.getImageData(0, 0, 1024, 1024), d = img.data;
  for (let i = 0; i < d.length; i += 4) { const n = (r() - .5) * 22; d[i] += n; d[i + 1] += n; d[i + 2] += n; }
  g.putImageData(img, 0, 0);
  g.globalAlpha = .07;
  for (let i = 0; i < 1400; i++) {
    g.strokeStyle = r() < .5 ? '#ffffff' : '#7f8c99'; g.lineWidth = .6 + r() * .8;
    const x = r() * 1024, y = r() * 1024, a = r() * Math.PI, l = 6 + r() * 26;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l); g.stroke();
  }
  g.globalAlpha = 1;
  return c;
}

// forro: negro con enrejado plateado fino
function linerCanvas() {
  const c = makeCanvas(1024, 1024), g = c.getContext('2d');
  g.fillStyle = '#121315'; g.fillRect(0, 0, 1024, 1024);
  g.strokeStyle = 'rgba(179,193,206,.34)'; g.lineWidth = 1.6;
  for (let i = -1024; i < 2048; i += 34) {
    g.beginPath(); g.moveTo(i, 0); g.lineTo(i + 1024, 1024); g.stroke();
    g.beginPath(); g.moveTo(i, 1024); g.lineTo(i + 1024, 0); g.stroke();
  }
  g.fillStyle = 'rgba(223,231,238,.5)';
  for (let x = 0; x < 1024; x += 34) for (let y = 17; y < 1024; y += 34) { g.beginPath(); g.arc(x, y, 1.6, 0, 7); g.fill(); }
  return c;
}

// tarjeta con los nombres
function cardCanvas() {
  const W = 1400, H = 975, c = makeCanvas(W, H), g = c.getContext('2d');
  const grd = g.createLinearGradient(0, 0, 0, H); grd.addColorStop(0, '#ffffff'); grd.addColorStop(1, '#f1f4f7');
  g.fillStyle = grd; g.fillRect(0, 0, W, H);
  const r = rng(3), img = g.getImageData(0, 0, W, H), d = img.data;
  for (let i = 0; i < d.length; i += 4) { const n = (r() - .5) * 7; d[i] += n; d[i + 1] += n; d[i + 2] += n; }
  g.putImageData(img, 0, 0);
  g.strokeStyle = '#b9c5d0'; g.lineWidth = 3; g.strokeRect(34, 34, W - 68, H - 68);
  g.strokeStyle = 'rgba(107,127,147,.4)'; g.lineWidth = 2; g.strokeRect(52, 52, W - 104, H - 104);
  g.textAlign = 'center'; g.textBaseline = 'middle';
  const spaced = (txt, y, size, color, sp) => {
    g.font = `500 ${size}px Montserrat, sans-serif`; g.fillStyle = color;
    const chars = [...txt]; const widths = chars.map(ch => g.measureText(ch).width);
    const total = widths.reduce((a, b) => a + b, 0) + sp * (chars.length - 1);
    let x = W / 2 - total / 2; g.textAlign = 'left';
    chars.forEach((ch, i) => { g.fillText(ch, x, y); x += widths[i] + sp; });
    g.textAlign = 'center';
  };
  spaced(String(INV.textos ? INV.textos.hero_kicker : 'Nos casamos').toUpperCase(), 268, 34, '#6b7178', 14);
  g.font = '190px "Pinyon Script", cursive'; g.fillStyle = '#3f5163';
  let nm = INV.novios || 'Sofía & Mateo', fsz = 190; g.font = fsz + 'px "Pinyon Script", cursive';
  while (g.measureText(nm).width > W - 200 && fsz > 90) { fsz -= 6; g.font = fsz + 'px "Pinyon Script", cursive'; }
  g.fillText(nm, W / 2, 470);
  const lg = g.createLinearGradient(W / 2 - 160, 0, W / 2 + 160, 0);
  lg.addColorStop(0, 'rgba(107,127,147,0)'); lg.addColorStop(.5, '#6b7f93'); lg.addColorStop(1, 'rgba(107,127,147,0)');
  g.fillStyle = lg; g.fillRect(W / 2 - 160, 620, 320, 3);
  g.save(); g.translate(W / 2, 621); g.rotate(Math.PI / 4); g.fillStyle = '#6b7f93'; g.fillRect(-7, -7, 14, 14); g.restore();
  spaced(INV.fechaCorta || '', 720, 34, '#6b7178', 12);
  return c;
}

// cara del sello: cera negra con anillo y monograma plateado
function sealCanvas() {
  const S = 1024, c = makeCanvas(S, S), g = c.getContext('2d');
  const grd = g.createRadialGradient(S * .4, S * .36, 20, S / 2, S / 2, S * .6);
  grd.addColorStop(0, '#3b4047'); grd.addColorStop(.55, '#17191c'); grd.addColorStop(1, '#050506');
  g.fillStyle = grd; g.fillRect(0, 0, S, S);
  g.strokeStyle = 'rgba(179,193,206,.85)'; g.lineWidth = 7;
  g.beginPath(); g.arc(S / 2, S / 2, S * .31, 0, 7); g.stroke();
  g.setLineDash([8, 14]); g.strokeStyle = 'rgba(223,231,238,.4)'; g.lineWidth = 3;
  g.beginPath(); g.arc(S / 2, S / 2, S * .275, 0, 7); g.stroke(); g.setLineDash([]);
  g.textAlign = 'center'; g.textBaseline = 'middle'; g.font = '250px "Pinyon Script", cursive';
  g.fillStyle = 'rgba(0,0,0,.75)'; g.fillText((INV.monograma || 'A&R'), S / 2 + 4, S / 2 + 22);
  const tg = g.createLinearGradient(0, S * .35, 0, S * .65);
  tg.addColorStop(0, '#ffffff'); tg.addColorStop(.5, '#c9d4de'); tg.addColorStop(1, '#8e9caa');
  g.fillStyle = tg; g.fillText((INV.monograma || 'A&R'), S / 2, S / 2 + 16);
  return c;
}
// relieve del sello (blanco = alto)
function sealBumpCanvas() {
  const S = 512, c = makeCanvas(S, S), g = c.getContext('2d');
  g.fillStyle = '#9a9a9a'; g.fillRect(0, 0, S, S);
  g.strokeStyle = '#5a5a5a'; g.lineWidth = 6; g.beginPath(); g.arc(S / 2, S / 2, S * .31, 0, 7); g.stroke();
  g.textAlign = 'center'; g.textBaseline = 'middle'; g.font = '125px "Pinyon Script", cursive';
  g.fillStyle = '#ffffff'; g.fillText((INV.monograma || 'A&R'), S / 2, S / 2 + 8);
  const r = rng(11);
  for (let i = 0; i < 2600; i++) { g.fillStyle = `rgba(${r() < .5 ? '255,255,255' : '0,0,0'},.06)`; g.fillRect(r() * S, r() * S, 3, 3); }
  return c;
}

function tex(canvas, srgb = true) {
  const t = new THREE.CanvasTexture(canvas);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4; return t;
}

async function waitFonts() {
  if (!document.fonts) return;
  try {
    await Promise.race([
      Promise.all([document.fonts.load('190px "Pinyon Script"'), document.fonts.load('500 34px Montserrat')]),
      new Promise(r => setTimeout(r, 2500))
    ]);
  } catch (e) { /* sin fuentes: usa las del sistema */ }
}

async function build() {
  const test = document.createElement('canvas');
  const gl = test.getContext('webgl2') || test.getContext('webgl');
  if (!gl) throw new Error('sin WebGL');

  await waitFonts();

  // ---------- escena ----------
  const canvas = document.createElement('canvas');
  canvas.id = 'sobre3d'; canvas.setAttribute('aria-hidden', 'true');
  intro.appendChild(canvas);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = .92;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(0x000000, 0);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), .04).texture;
  scene.environmentIntensity = .3;

  const camera = new THREE.PerspectiveCamera(32, 1, .1, 60);

  // luces
  scene.add(new THREE.HemisphereLight(0xdfe7ee, 0x0b0c0d, .35));
  const key = new THREE.DirectionalLight(0xffffff, 1.7);
  key.position.set(-2.6, 3.4, 5.2); key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024); key.shadow.radius = 6;
  key.shadow.camera.left = -4; key.shadow.camera.right = 4; key.shadow.camera.top = 4; key.shadow.camera.bottom = -4;
  key.shadow.bias = -0.0006; key.shadow.normalBias = .02;
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xb3c1ce, .9); rim.position.set(3, -1, 2.5); scene.add(rim);
  const glint = new THREE.PointLight(0xe8f0ff, 4.5, 7, 2); glint.position.set(0, .6, 1.6); scene.add(glint);

  // sombra proyectada detrás del sobre
  const wall = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), new THREE.ShadowMaterial({ opacity: .5 }));
  wall.position.z = -.75; wall.receiveShadow = true; scene.add(wall);

  // ---------- materiales ----------
  const W = 3.2, H = 2.2;
  const paper = tex(paperCanvas());
  const paperBump = tex(paperCanvas(), false);
  const paperMat = (hex) => new THREE.MeshStandardMaterial({ color: hex, map: paper, bumpMap: paperBump, bumpScale: .6, roughness: .82, metalness: 0 });
  const backMat = paperMat(0x4a5b6e);
  const sideMat = paperMat(0x7a8da1);
  const sideMat2 = paperMat(0x72859a);
  const bottomMat = paperMat(0x8a9cb0);
  const flapMat = paperMat(0x95a7b9);
  const linerTex = tex(linerCanvas()); linerTex.wrapS = linerTex.wrapT = THREE.RepeatWrapping;
  const linerMat = new THREE.MeshStandardMaterial({ map: linerTex, roughness: .55, metalness: .15 });

  // ---------- sobre ----------
  const root = new THREE.Group(); scene.add(root);
  const body = new THREE.Group(); root.add(body);

  const back = new THREE.Mesh(new THREE.BoxGeometry(W, H, .02), backMat);
  back.position.z = -.01; back.castShadow = true; back.receiveShadow = true; body.add(back);

  const liner = new THREE.Mesh(new THREE.PlaneGeometry(W - .16, H * .66), linerMat);
  liner.position.set(0, H * .14, .002); body.add(liner);

  // tarjeta
  const cardW = 2.82, cardH = cardW * 975 / 1400;
  const cardTex = tex(cardCanvas());
  const card = new THREE.Mesh(new THREE.BoxGeometry(cardW, cardH, .012),
    [new THREE.MeshStandardMaterial({ color: 0xf2f5f8, roughness: .7 }), new THREE.MeshStandardMaterial({ color: 0xf2f5f8, roughness: .7 }),
     new THREE.MeshStandardMaterial({ color: 0xf2f5f8, roughness: .7 }), new THREE.MeshStandardMaterial({ color: 0xf2f5f8, roughness: .7 }),
     new THREE.MeshStandardMaterial({ map: cardTex, roughness: .62 }), new THREE.MeshStandardMaterial({ color: 0xeef2f5, roughness: .7 })]);
  card.position.set(0, -.02, .012); card.castShadow = true; card.receiveShadow = true;
  root.add(card);

  // bolsillo frontal: tres triángulos con relieve
  function tri(points, mat, z, tiltAxis, tilt) {
    const s = new THREE.Shape(); s.moveTo(points[0][0], points[0][1]);
    for (let i = 1; i < points.length; i++) s.lineTo(points[i][0], points[i][1]);
    s.closePath();
    const geo = new THREE.ExtrudeGeometry(s, { depth: .006, bevelEnabled: true, bevelThickness: .004, bevelSize: .006, bevelSegments: 2 });
    const uv = geo.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) / W + .5, uv.getY(i) / H + .5);
    const m = new THREE.Mesh(geo, mat); m.position.z = z; m.castShadow = true; m.receiveShadow = true;
    if (tiltAxis) { m.rotation[tiltAxis] = tilt; }
    body.add(m); return m;
  }
  const yC = -.02;
  tri([[-W / 2, H / 2], [-W / 2, -H / 2], [.05, yC]], sideMat, .02);
  tri([[W / 2, H / 2], [W / 2, -H / 2], [-.05, yC]], sideMat2, .022);
  const bottomShape = [[-W / 2, -H / 2], [W / 2, -H / 2], [.14, yC + .08], [0, yC + .12], [-.14, yC + .08]];
  const bottom = tri(bottomShape, bottomMat, .03);

  // solapa con bisagra en el borde superior
  const mouth = new THREE.Object3D(); mouth.position.set(0, H / 2, .05); body.add(mouth);   // boca del sobre, de ahí salen los pétalos
  const flapPivot = new THREE.Group(); flapPivot.position.set(0, H / 2, .045); body.add(flapPivot);
  const fs = new THREE.Shape();
  fs.moveTo(-W / 2, 0); fs.lineTo(W / 2, 0); fs.lineTo(.16, -H * .6 + .05);
  fs.quadraticCurveTo(0, -H * .6 - .03, -.16, -H * .6 + .05); fs.closePath();
  const flapGeo = new THREE.ExtrudeGeometry(fs, { depth: .006, bevelEnabled: true, bevelThickness: .004, bevelSize: .006, bevelSegments: 2 });
  const fuv = flapGeo.attributes.uv; for (let i = 0; i < fuv.count; i++) fuv.setXY(i, fuv.getX(i) / W + .5, fuv.getY(i) / H + .5);
  const flap = new THREE.Mesh(flapGeo, flapMat); flap.castShadow = true; flap.receiveShadow = true; flapPivot.add(flap);
  const flapLiner = new THREE.Mesh(new THREE.ShapeGeometry(fs), linerMat.clone());
  flapLiner.material.side = THREE.BackSide; flapLiner.position.z = -.003; flapLiner.scale.set(.93, .93, 1); flapPivot.add(flapLiner);
  const fluv = flapLiner.geometry.attributes.uv; for (let i = 0; i < fluv.count; i++) fluv.setXY(i, fluv.getX(i) / W + .5, fluv.getY(i) / H + .5);

  // ---------- sello de cera (dos mitades que se separan) ----------
  const sealTex = tex(sealCanvas()), sealBump = tex(sealBumpCanvas(), false);
  const R = .36, r2 = rng(5), noisy = [];
  for (let i = 0; i < 64; i++) { const a = i / 64 * Math.PI * 2; noisy.push(R * (1 + .045 * Math.sin(a * 7) + .03 * Math.sin(a * 13 + 1) + (r2() - .5) * .03)); }
  const radAt = a => { const f = ((a % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2) / (Math.PI * 2) * 64; const i = Math.floor(f), t = f - i; return lerp(noisy[i % 64], noisy[(i + 1) % 64], t); };
  const crack = [[.0, R * 1.1], [.04, R * .55], [-.03, R * .2], [.035, -R * .15], [-.02, -R * .55], [.01, -R * 1.1]];
  function sealHalf(side) {
    const s = new THREE.Shape();
    s.moveTo(crack[0][0], crack[0][1]);
    crack.forEach(p => s.lineTo(p[0], p[1]));
    const a0 = -Math.PI / 2, steps = 32;
    for (let i = 0; i <= steps; i++) {
      const a = side > 0 ? a0 + (i / steps) * Math.PI : a0 - (i / steps) * Math.PI;
      const rr = radAt(a); s.lineTo(Math.cos(a) * rr, Math.sin(a) * rr);
    }
    s.closePath();
    const geo = new THREE.ExtrudeGeometry(s, { depth: .05, bevelEnabled: true, bevelThickness: .035, bevelSize: .03, bevelSegments: 5, curveSegments: 24 });
    const uv = geo.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) / (2 * R * 1.08) + .5, uv.getY(i) / (2 * R * 1.08) + .5);
    const capMat = new THREE.MeshPhysicalMaterial({ map: sealTex, bumpMap: sealBump, bumpScale: 2.2, roughness: .38, metalness: .05, clearcoat: 1, clearcoatRoughness: .25 });
    const sideM = new THREE.MeshPhysicalMaterial({ color: 0x0c0d0f, roughness: .35, clearcoat: 1, clearcoatRoughness: .3 });
    const m = new THREE.Mesh(geo, [capMat, sideM]); m.castShadow = true;
    return m;
  }
  const seal = new THREE.Group(); flapPivot.add(seal);
  seal.position.set(0, -H * .6 + .17, .02);
  const halfL = sealHalf(-1), halfR = sealHalf(1); seal.add(halfL, halfR);
  // anillo de luz que invita a tocar
  const ring = new THREE.Mesh(new THREE.RingGeometry(.47, .485, 96), new THREE.MeshBasicMaterial({ color: 0xdfe7ee, transparent: true, opacity: .5, depthWrite: false }));
  ring.position.z = .1; seal.add(ring);

  // ---------- encuadre ----------
  let aspect = 1, baseDist = 8;
  const look = new THREE.Vector3(0, .08, 0);
  function fit() {
    const w = intro.clientWidth, h = intro.clientHeight;
    renderer.setSize(w, h, false); canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
    aspect = w / h; camera.aspect = aspect;
    const vt = 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const dW = (W / .84) / (vt * aspect), dH = (H / .36) / vt;
    baseDist = Math.max(dW, dH);
    camera.updateProjectionMatrix();
  }
  fit(); addEventListener('resize', fit);
  camera.position.set(0, .08, baseDist); camera.lookAt(look);

  // movimiento con el dedo / ratón
  let px = 0, py = 0, tx = 0, ty = 0;
  intro.addEventListener('pointermove', e => { tx = (e.clientX / innerWidth - .5) * 2; ty = (e.clientY / innerHeight - .5) * 2; }, { passive: true });

  // ---------- animación ----------
  const clock = new THREE.Clock();
  let openAt = null, running = true, onDone = null, burstFired = false, onBurst = null;
  const halfVel = [];

  function project(obj) {
    const v = new THREE.Vector3(); obj.getWorldPosition(v); v.project(camera);
    return { x: (v.x + 1) / 2 * intro.clientWidth, y: (1 - v.y) / 2 * intro.clientHeight };
  }

  function frame() {
    if (!running) return;
    const t = clock.getElapsedTime();
    px += (tx - px) * .05; py += (ty - py) * .05;

    if (openAt === null) {
      // reposo: flota y sigue al dedo
      root.rotation.y = Math.sin(t * .45) * .07 + px * .16;
      root.rotation.x = -.04 + Math.sin(t * .6) * .025 + py * .1;
      root.position.y = Math.sin(t * .8) * .045;
      const p = (t % 2.4) / 2.4;
      ring.scale.setScalar(1 + p * .45); ring.material.opacity = .55 * (1 - p);
    } else {
      const k = window.__envT !== undefined ? window.__envT : (t - openAt) * (reduce ? 1.6 : 1);
      // el reposo se apaga suavemente
      const settle = easeOut(seg(k, 0, 1.6));
      root.rotation.y *= (1 - .06 * settle); root.rotation.x *= (1 - .06 * settle); root.position.y *= .95;
      ring.material.opacity = 0;
      // 1) el sello se rompe y sus mitades caen
      if (k < 2.2) {
        const s = seg(k, 0, .15);
        [halfL, halfR].forEach((h, i) => {
          const dir = i === 0 ? -1 : 1;
          if (!halfVel[i]) halfVel[i] = { vx: dir * (.9 + Math.random() * .3), vy: .9, vz: 1.4, rz: dir * (2.5 + Math.random()), rx: 1.2 + Math.random() };
          const v = halfVel[i], tt = Math.max(0, k - .08);
          h.position.set(v.vx * tt, v.vy * tt - 4.2 * tt * tt, v.vz * tt);
          h.rotation.set(v.rx * tt, 0, v.rz * tt);
          h.scale.setScalar(1 + s * .04);
        });
      }
      // 2) la solapa se abre con peso de papel
      const fo = easeInOut(seg(k, .28, 1.35));
      flapPivot.rotation.x = fo * Math.PI * .93;
      flapPivot.position.z = .045 - fo * .03;
      // 3) la tarjeta sale del sobre
      const cu = easeOut(seg(k, 1.05, 2.25));
      card.position.y = -.02 + cu * (H * .74);
      card.position.z = .012;
      if (cu > .98) card.position.z = .012 + seg(k, 2.25, 2.6) * .08;
      if (!burstFired && k > 1.25) { burstFired = true; onBurst && onBurst(project(mouth)); }
      // 4) el sobre cae y la cámara se acerca a la tarjeta
      const dz = easeInOut(seg(k, 2.25, 3.55));
      body.position.y = -easeIn(seg(k, 2.25, 3.35)) * 5;
      body.rotation.x = easeIn(seg(k, 2.25, 3.35)) * .5;
      const cardWorld = new THREE.Vector3(); card.getWorldPosition(cardWorld);
      const vt = 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
      const closeDist = Math.max((cardW / .9) / (vt * aspect), (cardH / .7) / vt);
      camera.position.set(lerp(0, cardWorld.x, dz), lerp(.08, cardWorld.y, dz), lerp(baseDist, cardWorld.z + closeDist, dz));
      look.set(lerp(0, cardWorld.x, dz), lerp(.08, cardWorld.y, dz), lerp(0, cardWorld.z, dz));
      card.rotation.x = lerp(card.rotation.x, 0, dz);
      if (k > 3.6 && onDone) { const f = onDone; onDone = null; f(); }
    }
    // destello de luz que recorre el papel y la cera
    glint.position.x = Math.sin(t * .55) * 2.2; glint.position.y = .5 + Math.cos(t * .4) * .9;
    camera.lookAt(look);
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }

  window.env3d = {
    ready: true,
    open(burstCb, doneCb) { if (openAt !== null) return; onBurst = burstCb; onDone = doneCb; root.attach(seal); openAt = clock.getElapsedTime(); },
    stop() {
      running = false;
      setTimeout(() => { renderer.dispose(); pmrem.dispose(); canvas.remove(); }, 400);
    }
  };
  canvas.addEventListener('click', () => window.openInvitation && window.openInvitation());
  intro.classList.add('has3d');
  intro.classList.remove('loading3d');
  frame();
}

build().catch(err => {
  console.warn('Sobre 3D no disponible, se usa el sobre clásico:', err);
  intro.classList.remove('loading3d');
});
})();
