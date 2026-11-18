/* Efectos de la invitación: fondo animado, explosión al abrir el sobre, gran final y estela al tocar.
   Los pétalos y los fuegos artificiales viven en index.html; aquí están todos los demás. */
(function(){
  const CFG = window.INV || {};
  const E = CFG.efectos || {};
  const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const FONDO = E.fondo || "ninguno", APERTURA = E.apertura || "ninguno", FINAL = E.final || "ninguno";
  const usarFondo = !["petalos", "ninguno"].includes(FONDO);
  const usarApertura = !["petalos", "ninguno"].includes(APERTURA);
  const usarFinal = !["fuegos", "ninguno"].includes(FINAL);
  if (APERTURA === "ninguno") window.petalBurst = function(){};
  if (reduce || (!usarFondo && !usarApertura && !usarFinal && !E.toque)) return;

  // Paleta (se adapta sola a la paleta elegida en el editor)
  const C = { blanco:"#ffffff", perla:"#eef3f7", claro:"#dfe7ee", plata:"#b3c1ce", medio:"#8fa3b7", oscuro:"#6b7f93", profundo:"#3f5163", oro:"#e9d9b0", oro2:"#cdb27a", rosa:"#f3d3da", rojo:"#d7546a" };

  const cv = document.createElement("canvas");
  cv.id = "fx"; cv.setAttribute("aria-hidden", "true");
  cv.style.cssText = "position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:61";
  document.body.appendChild(cv);
  const ctx = cv.getContext("2d");
  let W, H, dpr;
  function resize(){ dpr = Math.min(window.devicePixelRatio || 1, 2); W = cv.width = innerWidth * dpr; H = cv.height = innerHeight * dpr; }
  resize(); addEventListener("resize", resize);
  const R = (a, b) => a + Math.random() * (b - a);
  const pick = a => a[Math.random() * a.length | 0];

  // ---------- sprites dibujados una sola vez ----------
  function sprite(size, draw){ const c = document.createElement("canvas"); c.width = c.height = size; draw(c.getContext("2d"), size); return c; }
  const glow = (col) => sprite(64, (g, s) => { const r = g.createRadialGradient(s/2, s/2, 0, s/2, s/2, s/2);
    r.addColorStop(0, "#ffffff"); r.addColorStop(.25, col); r.addColorStop(1, "rgba(0,0,0,0)"); g.fillStyle = r; g.fillRect(0, 0, s, s); });
  const heart = (col, edge) => sprite(64, (g, s) => { g.translate(s/2, s/2 + 3); g.scale(1.35, 1.35);
    g.beginPath(); g.moveTo(0, 10); g.bezierCurveTo(-22, -4, -12, -22, 0, -10); g.bezierCurveTo(12, -22, 22, -4, 0, 10); g.closePath();
    const lg = g.createLinearGradient(-12, -16, 12, 12); lg.addColorStop(0, "#ffffff"); lg.addColorStop(.35, col); lg.addColorStop(1, edge);
    g.fillStyle = lg; g.shadowColor = "rgba(0,0,0,.25)"; g.shadowBlur = 4; g.fill(); });
  const star = (col) => sprite(64, (g, s) => { g.translate(s/2, s/2);
    const r = g.createRadialGradient(0, 0, 0, 0, 0, 30); r.addColorStop(0, "rgba(255,255,255,.9)"); r.addColorStop(.2, col); r.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = r; g.beginPath(); for (let i = 0; i < 8; i++){ const a = i * Math.PI / 4, rr = i % 2 ? 6 : 30; g.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); } g.closePath(); g.fill(); });
  const flake = sprite(64, (g, s) => { g.translate(s/2, s/2); g.strokeStyle = "rgba(255,255,255,.95)"; g.lineWidth = 2.2; g.lineCap = "round";
    for (let i = 0; i < 6; i++){ g.rotate(Math.PI / 3); g.beginPath(); g.moveTo(0, 0); g.lineTo(0, -24); g.moveTo(0, -12); g.lineTo(-6, -18); g.moveTo(0, -12); g.lineTo(6, -18); g.stroke(); } });
  const leaf = (col, vein) => sprite(64, (g, s) => { g.translate(s/2, s/2); g.rotate(-.5);
    g.beginPath(); g.moveTo(0, -26); g.quadraticCurveTo(18, -6, 0, 26); g.quadraticCurveTo(-18, -6, 0, -26); g.closePath();
    const lg = g.createLinearGradient(-10, -20, 10, 20); lg.addColorStop(0, col); lg.addColorStop(1, vein); g.fillStyle = lg; g.fill();
    g.strokeStyle = "rgba(255,255,255,.35)"; g.lineWidth = 1.2; g.beginPath(); g.moveTo(0, -22); g.lineTo(0, 24); g.stroke(); });
  const bubble = sprite(64, (g, s) => { const c = s/2; g.strokeStyle = "rgba(255,255,255,.55)"; g.lineWidth = 1.6; g.beginPath(); g.arc(c, c, 26, 0, 7); g.stroke();
    const r = g.createRadialGradient(c - 9, c - 9, 1, c, c, 28); r.addColorStop(0, "rgba(255,255,255,.55)"); r.addColorStop(.35, "rgba(255,255,255,.06)"); r.addColorStop(1, "rgba(223,231,238,.18)");
    g.fillStyle = r; g.beginPath(); g.arc(c, c, 26, 0, 7); g.fill(); });
  const lantern = sprite(96, (g, s) => { const r = g.createRadialGradient(48, 52, 2, 48, 52, 46); r.addColorStop(0, "rgba(255,226,170,.85)"); r.addColorStop(1, "rgba(255,200,120,0)");
    g.fillStyle = r; g.fillRect(0, 0, s, s); g.fillStyle = "#ffe7b8"; g.beginPath(); g.moveTo(34, 30); g.lineTo(62, 30); g.lineTo(58, 70); g.lineTo(38, 70); g.closePath(); g.fill();
    g.fillStyle = "#ffb85c"; g.fillRect(40, 64, 16, 6); });

  const SPR = {
    corazones: [heart(C.rosa, C.rojo), heart(C.blanco, C.plata), heart(C.claro, C.medio)],
    luciernagas: [glow("#fff2c4"), glow(C.oro)],
    destellos: [star(C.blanco), star(C.claro), star(C.oro)],
    nieve: [flake],
    hojas: [leaf("#9cae6b", "#5d6e3a"), leaf("#c9a46a", "#8a6334"), leaf(C.medio, C.profundo)],
    burbujas: [bubble],
    linternas: [lantern]
  };
  const CONFETI = [C.blanco, C.claro, C.plata, C.medio, C.oro, C.oro2, C.profundo];

  // ---------- partículas ----------
  let ambient = [], extra = [], paused = false, fade = 1;
  function nueva(tipo, x, y, burst){
    const p = { tipo, x, y, life: 1, rot: R(0, 6.28), vr: R(-.02, .02), ph: R(0, 6.28), burst };
    const s = dpr;
    switch (tipo){
      case "corazones": Object.assign(p, { size: R(12, 26) * s, vx: 0, vy: R(.3, .8) * s, sp: pick(SPR.corazones), a: R(.6, .95) }); break;
      case "luciernagas": Object.assign(p, { size: R(10, 22) * s, vx: R(-.3, .3) * s, vy: R(-.35, .1) * s, sp: pick(SPR.luciernagas), a: 1, tw: R(.02, .05) }); break;
      case "destellos": Object.assign(p, { size: R(8, 22) * s, vx: R(-.1, .1) * s, vy: R(.05, .3) * s, sp: pick(SPR.destellos), a: 1, tw: R(.03, .07) }); break;
      case "nieve": Object.assign(p, { size: R(8, 20) * s, vx: 0, vy: R(.4, 1.1) * s, sp: SPR.nieve[0], a: R(.5, .95) }); break;
      case "hojas": Object.assign(p, { size: R(16, 30) * s, vx: 0, vy: R(.5, 1.1) * s, sp: pick(SPR.hojas), a: R(.75, 1), vr: R(-.035, .035) }); break;
      case "burbujas": Object.assign(p, { size: R(10, 30) * s, vx: 0, vy: -R(.35, .9) * s, sp: SPR.burbujas[0], a: R(.5, .9) }); break;
      case "confeti": Object.assign(p, { w: R(5, 9) * s, h: R(9, 15) * s, vx: R(-.2, .2) * s, vy: R(.6, 1.4) * s, col: pick(CONFETI), a: 1, flip: R(0, 6.28), vf: R(.05, .15) }); break;
      case "linternas": Object.assign(p, { size: R(34, 60) * s, vx: R(-.15, .15) * s, vy: -R(.5, 1.0) * s, sp: SPR.linternas[0], a: 1 }); break;
    }
    if (burst){ const ang = R(-Math.PI * .92, -Math.PI * .08), v = R(3, 9) * s; p.vx = Math.cos(ang) * v; p.vy = Math.sin(ang) * v; p.drag = .965; p.g = (tipo === "burbujas" || tipo === "linternas" ? -.02 : .09) * s; }
    return p;
  }
  function reiniciar(p){
    const sube = p.tipo === "burbujas" || p.tipo === "linternas" || p.tipo === "luciernagas";
    Object.assign(p, nueva(p.tipo, R(0, W), sube ? H + R(10, 80) * dpr : -R(10, 80) * dpr, false));
  }
  if (usarFondo){
    const n = { corazones: 18, luciernagas: 26, destellos: 30, nieve: 40, hojas: 16, burbujas: 22, confeti: 34 }[FONDO] || 20;
    for (let i = 0; i < (innerWidth < 700 ? n : n * 1.6); i++) ambient.push(nueva(FONDO, R(0, W), R(0, H), false));
  }

  function mover(p, t){
    p.ph += .02; p.rot += p.vr;
    if (p.burst){ p.vx *= p.drag; p.vy = p.vy * p.drag + p.g; p.x += p.vx; p.y += p.vy; p.life -= .006; return; }
    switch (p.tipo){
      case "luciernagas": p.x += p.vx + Math.sin(p.ph * 1.3) * .5 * dpr; p.y += p.vy + Math.cos(p.ph) * .3 * dpr; break;
      case "confeti": p.flip += p.vf; p.x += p.vx + Math.sin(p.ph) * .8 * dpr; p.y += p.vy; break;
      default: p.x += p.vx + Math.sin(p.ph) * .6 * dpr; p.y += p.vy;
    }
    if (p.x < -60 * dpr) p.x = W + 40 * dpr; if (p.x > W + 60 * dpr) p.x = -40 * dpr;
  }
  function fuera(p){ return p.y > H + 90 * dpr || p.y < -110 * dpr; }
  function dibujar(p, alphaMul){
    let a = p.a * Math.max(0, p.life) * alphaMul;
    if (p.tw) a *= .45 + .55 * Math.abs(Math.sin(p.ph * p.tw * 40));
    if (a <= .01) return;
    ctx.globalAlpha = Math.min(1, a);
    ctx.setTransform(1, 0, 0, 1, p.x, p.y); ctx.rotate(p.rot);
    if (p.tipo === "confeti"){ ctx.scale(1, Math.cos(p.flip)); ctx.fillStyle = p.col; ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h); }
    else { const s = p.size; ctx.drawImage(p.sp, -s / 2, -s / 2, s, s); }
  }

  // ---------- apertura del sobre ----------
  if (usarApertura){
    const tipo = APERTURA === "corazones" ? "corazones" : APERTURA === "destellos" ? "destellos" : "confeti";
    window.petalBurst = function(cx, cy){ for (let i = 0; i < 70; i++) extra.push(nueva(tipo, cx * dpr + R(-30, 30) * dpr, cy * dpr, true)); };
  }

  // ---------- gran final al llegar al pie ----------
  let finalHasta = 0, siguiente = 0;
  function lanzarFinal(now){
    if (FINAL === "confeti"){
      for (const lado of [0, 1]) for (let i = 0; i < 70; i++){
        const p = nueva("confeti", lado ? W - 10 * dpr : 10 * dpr, H - 10 * dpr, false);
        const ang = lado ? R(-Math.PI * .85, -Math.PI * .6) : R(-Math.PI * .4, -Math.PI * .15), v = R(10, 20) * dpr;
        Object.assign(p, { vx: Math.cos(ang) * v, vy: Math.sin(ang) * v, burst: true, drag: .975, g: .16 * dpr }); extra.push(p);
      }
    } else if (FINAL === "corazones"){
      for (let i = 0; i < 6; i++){ const p = nueva("corazones", R(0, W), -R(10, 90) * dpr, false); p.vy = R(1.2, 2.4) * dpr; p.size *= 1.3; p.fin = true; extra.push(p); }
    } else if (FINAL === "linternas"){
      for (let i = 0; i < 2; i++){ const p = nueva("linternas", R(.1, .9) * W, H + R(20, 80) * dpr, false); p.fin = true; extra.push(p); }
    } else if (FINAL === "destellos"){
      const cx = R(.2, .8) * W, cy = R(.15, .5) * H;
      for (let i = 0; i < 40; i++){ const p = nueva("destellos", cx, cy, true); p.size *= 1.4; extra.push(p); }
    }
  }
  if (usarFinal){
    const footer = document.querySelector("footer");
    if (footer){
      new IntersectionObserver(es => es.forEach(e => {
        paused = e.isIntersecting; window.petalsPaused = e.isIntersecting;
        if (e.isIntersecting){ finalHasta = performance.now() + 8000; siguiente = 0; }
      }), { threshold: .2 }).observe(footer);
      footer.addEventListener("click", () => { finalHasta = performance.now() + 5000; siguiente = 0; });
    }
  } else if (usarFondo){
    const footer = document.querySelector("footer");
    if (footer) new IntersectionObserver(es => es.forEach(e => { paused = e.isIntersecting && FINAL === "fuegos"; }), { threshold: .2 }).observe(footer);
  }

  // ---------- estela al tocar ----------
  if (E.toque){
    const add = (x, y, n) => { for (let i = 0; i < n; i++){ const p = nueva("destellos", x * dpr, y * dpr, true); p.size *= .55; p.drag = .9; p.g = .02 * dpr; p.vx *= .25; p.vy *= .25; p.life = .7; extra.push(p); } };
    addEventListener("pointermove", e => { if (e.pointerType !== "mouse" || Math.random() < .5) add(e.clientX, e.clientY, 1); }, { passive: true });
    addEventListener("pointerdown", e => add(e.clientX, e.clientY, 8), { passive: true });
  }

  function frame(now){
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, W, H);
    fade = paused ? Math.max(0, fade - .03) : Math.min(1, fade + .02);
    if (usarFinal && now < finalHasta && now >= siguiente){
      lanzarFinal(now);
      siguiente = now + ({ confeti: 1800, corazones: 260, linternas: 520, destellos: 700 }[FINAL] || 800);
    }
    for (const p of ambient){ mover(p, now); if (fuera(p)) reiniciar(p); dibujar(p, fade); }
    extra = extra.filter(p => p.life > 0 && !(fuera(p) && !p.burst) && p.y < H + 200 * dpr && p.y > -400 * dpr);
    for (const p of extra){ mover(p, now); dibujar(p, 1); }
    ctx.globalAlpha = 1;
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
