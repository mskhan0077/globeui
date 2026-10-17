/* Dr Octopus: a violet, big-eyed octopus that pulls the day/night divider back to the
   right whenever it's slid left (js/story/opening.js).

   Slide left (drag or ←) and the octopus rises on the right, grabs the handle with one
   tentacle and holds on: the tentacle stretches and goes taut as you pull. Let go and it
   tugs the divider back to where the drag started, then bounces, lets go and sinks away.
   The tug drives the divider through `setTransition` on every animation frame, and the
   tentacle is drawn to the handle's on-screen position each frame, so the octopus, the
   slider and the island stay in sync.

   const octo = createOctopus(stage, handle, { setTransition, getTransition });
   octo.grab()   on pointerdown (before the handle moves)
   octo.moved()  after each user move
   octo.release() on pointerup / keyboard pause
   octo.hide()   when the landing page goes away */

const COLORS = {
  light: '#c4b5fd', mid: '#8b5cf6', deep: '#6d28d9', dark: '#4c1d95',
  sucker: '#ede9fe', cheek: '#f9a8d4', pupil: '#130a2a',
};
const START_THRESHOLD = 0.01;  // share of the width slid left before the octopus appears
const ENTER_MS = 380;          // rising from the water
const EXIT_DELAY_MS = 750;     // after the tug: bounce, then sink away
const EXIT_MS = 420;
const SIZE = 1.3;              // head + hanging arms scale (the pulling arm always reaches the handle)

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2); // ease-in-out cubic
const clamp01 = (t) => Math.min(1, Math.max(0, t));

export function createOctopus(stage, handle, { setTransition, getTransition }) {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const divider = handle.parentElement;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'octopus');
  svg.setAttribute('aria-hidden', 'true');
  svg.innerHTML = `
    <defs>
      <radialGradient id="octo-skin" cx="38%" cy="32%" r="75%">
        <stop offset="0" stop-color="${COLORS.light}"/>
        <stop offset="0.55" stop-color="${COLORS.mid}"/>
        <stop offset="1" stop-color="${COLORS.deep}"/>
      </radialGradient>
      <linearGradient id="octo-arm" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="${COLORS.deep}"/>
        <stop offset="1" stop-color="${COLORS.mid}"/>
      </linearGradient>
    </defs>
    <g class="octopus__body"></g>`;
  stage.appendChild(svg);
  const body = svg.querySelector('.octopus__body');

  // ---------- state ----------
  let mode = 'off';        // off | holding (user pulling left) | tugging | done | leaving
  let start = 0;           // divider position when the drag began (where the tug returns to)
  let anchor = null;       // octopus head position, fixed while it holds on
  let shownAt = 0, modeAt = 0;
  let frame = 0;
  let tug = null;          // { from, to, t0, dur }
  let nextBlink = 0, blinkUntil = 0;

  // ---------- geometry ----------
  function handlePoint() {
    const s = stage.getBoundingClientRect();
    const h = handle.getBoundingClientRect();
    return { x: h.left + h.width / 2 - s.left, y: h.top + h.height / 2 - s.top, w: s.width, h: s.height };
  }

  // Tapered arm from p0 (thick) to p3 (thin) along a cubic Bézier, with suckers.
  function arm(p0, c1, c2, p3, w0, w1, suckers = true) {
    const n = 26, left = [], right = [], dots = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n, u = 1 - t;
      const x = u * u * u * p0.x + 3 * u * u * t * c1.x + 3 * u * t * t * c2.x + t * t * t * p3.x;
      const y = u * u * u * p0.y + 3 * u * u * t * c1.y + 3 * u * t * t * c2.y + t * t * t * p3.y;
      const dx = 3 * u * u * (c1.x - p0.x) + 6 * u * t * (c2.x - c1.x) + 3 * t * t * (p3.x - c2.x);
      const dy = 3 * u * u * (c1.y - p0.y) + 6 * u * t * (c2.y - c1.y) + 3 * t * t * (p3.y - c2.y);
      const len = Math.hypot(dx, dy) || 1, nx = -dy / len, ny = dx / len;
      const w = (w0 + (w1 - w0) * t) / 2;
      left.push(`${(x + nx * w).toFixed(1)},${(y + ny * w).toFixed(1)}`);
      right.push(`${(x - nx * w).toFixed(1)},${(y - ny * w).toFixed(1)}`);
      if (suckers && i % 3 === 1 && i < n - 1) {
        dots.push(`<circle cx="${(x - nx * w * 0.45).toFixed(1)}" cy="${(y - ny * w * 0.45).toFixed(1)}" r="${Math.max(1.1, w * 0.42).toFixed(1)}" fill="${COLORS.sucker}" opacity="0.85"/>`);
      }
    }
    return `<path d="M${left.join(' L')} L${right.reverse().join(' L')} Z" fill="url(#octo-arm)"/>${dots.join('')}`;
  }

  // ---------- drawing ----------
  function draw(now) {
    const hp = handlePoint();
    const t = now / 1000;
    const since = now - shownAt;
    const enter = reducedMotion ? 1 : ease(clamp01(since / ENTER_MS));
    const leaving = mode === 'leaving' ? clamp01((now - modeAt) / EXIT_MS) : 0;
    const holdingArm = mode !== 'leaving' || leaving < 0.35;   // lets go at the start of leaving

    // Head: anchored where it rose, bobbing gently; sinks while leaving.
    const bob = reducedMotion ? 0 : Math.sin(t * 2.4) * 2.5;
    const cx = anchor.x;
    const cy = anchor.y + bob + (1 - enter) * 70 + ease(leaving) * 90;
    const stretch = Math.max(0, cx - hp.x - 130);              // how far the arm is stretched
    const pulling = mode === 'tugging';
    const happy = mode === 'done';
    // lean: pulled towards the handle while holding, leans back while tugging, bounces when done
    let lean = mode === 'holding' ? -Math.min(14, stretch * 0.05) : pulling ? 9 : 0;
    let squash = 1 + (reducedMotion ? 0 : Math.sin(t * 2.4 + 1) * 0.025);
    if (happy && !reducedMotion) {
      const b = clamp01((now - modeAt) / 420);
      squash *= 1 + Math.sin(b * Math.PI * 2) * 0.08 * (1 - b);
    }

    let out = '';
    const scaled = `<g transform="translate(${cx.toFixed(1)} ${cy.toFixed(1)}) scale(${SIZE}) translate(${(-cx).toFixed(1)} ${(-cy).toFixed(1)})">`;
    let figure = '';   // head + hanging arms, drawn at SIZE around the head centre
    // Idle arms hanging below the head
    for (let i = 0; i < 6; i++) {
      const a = (i - 2.5) / 2.5;                                  // -1 … 1 across the bottom
      const sway = reducedMotion ? 0 : Math.sin(t * 2.2 + i * 1.3) * 7;
      const p0 = { x: cx + a * 22, y: cy + 20 };
      const p3 = { x: cx + a * 40 + sway, y: cy + 66 + Math.abs(a) * -6 };
      figure += arm(p0, { x: p0.x + a * 6, y: p0.y + 18 }, { x: p3.x - sway * 0.8, y: p3.y - 22 }, p3, 10, 3, i % 2 === 0);
      // curled tip
      figure += `<circle cx="${(p3.x + (a >= 0 ? 2.5 : -2.5)).toFixed(1)}" cy="${(p3.y - 2).toFixed(1)}" r="2.6" fill="none" stroke="${COLORS.mid}" stroke-width="2"/>`;
    }

    // The pulling arm: from the head's lower left to the handle, coiled around it.
    if (holdingArm) {
      const p0 = { x: cx - 26 * SIZE, y: cy + 14 * SIZE };
      const tip = { x: hp.x + 15, y: hp.y + 6 };
      const dist = Math.hypot(p0.x - tip.x, p0.y - tip.y);
      const sag = Math.max(5, 34 - dist * 0.07) + (reducedMotion ? 0 : Math.sin(t * 5) * (pulling ? 4 : 2));
      const c1 = { x: p0.x - dist * 0.32, y: p0.y + sag };
      const c2 = { x: tip.x + dist * 0.28, y: tip.y + sag * 0.9 };
      out += arm(p0, c1, c2, tip, 13, 5);
      // coil wrapped around the handle (front part drawn over it)
      const r = 17;
      const a0 = -0.6, a1 = Math.PI * 1.25;
      const arc = (x, y, from, to) => {
        const sx = x + r * Math.cos(from), sy = y + r * Math.sin(from);
        const ex = x + r * Math.cos(to), ey = y + r * Math.sin(to);
        return `M${sx.toFixed(1)},${sy.toFixed(1)} A${r},${r} 0 1,1 ${ex.toFixed(1)},${ey.toFixed(1)}`;
      };
      out += `<path d="${arc(hp.x, hp.y + 4, a0, a1)}" fill="none" stroke="${COLORS.mid}" stroke-width="5.5" stroke-linecap="round"/>`;
      out += `<path d="${arc(hp.x, hp.y + 4, a0, a1)}" fill="none" stroke="${COLORS.light}" stroke-width="1.6" stroke-linecap="round" stroke-dasharray="1.5 6" opacity="0.9"/>`;
    }

    // Head
    figure += `<g transform="rotate(${lean.toFixed(1)} ${cx.toFixed(1)} ${(cy + 18).toFixed(1)})">`;
    figure += `<ellipse cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" rx="${(36 / squash).toFixed(1)}" ry="${(33 * squash).toFixed(1)}" fill="url(#octo-skin)"/>`;
    figure += `<circle cx="${(cx - 14).toFixed(1)}" cy="${(cy - 20).toFixed(1)}" r="3.5" fill="${COLORS.light}" opacity="0.55"/>`;
    figure += `<circle cx="${(cx + 16).toFixed(1)}" cy="${(cy - 16).toFixed(1)}" r="2.6" fill="${COLORS.light}" opacity="0.5"/>`;
    figure += `<circle cx="${(cx + 4).toFixed(1)}" cy="${(cy - 26).toFixed(1)}" r="2" fill="${COLORS.light}" opacity="0.45"/>`;

    // Big eyes: look at the handle; wide while being pulled, squint while tugging, blink.
    if (!reducedMotion && now > nextBlink) { blinkUntil = now + 130; nextBlink = now + 2400 + Math.random() * 2200; }
    const blink = now < blinkUntil;
    const lookX = Math.max(-1, Math.min(1, (hp.x - cx) / 160)) * 3.2;
    const lookY = Math.max(-1, Math.min(1, (hp.y - cy) / 160)) * 2.4;
    const eyeRy = blink ? 1.5 : pulling ? 8.5 : happy ? 7 : 13.5;
    for (const side of [-1, 1]) {
      const ex = cx + side * 14, ey = cy + 1;
      figure += `<ellipse cx="${ex.toFixed(1)}" cy="${ey.toFixed(1)}" rx="12.5" ry="${eyeRy}" fill="#fff" stroke="${COLORS.dark}" stroke-width="1.2"/>`;
      if (!blink) {
        const ir = Math.min(7.5, eyeRy * 0.62);
        figure += `<circle cx="${(ex + lookX).toFixed(1)}" cy="${(ey + lookY * (eyeRy / 13.5)).toFixed(1)}" r="${ir.toFixed(1)}" fill="${COLORS.dark}"/>`;
        figure += `<circle cx="${(ex + lookX).toFixed(1)}" cy="${(ey + lookY * (eyeRy / 13.5)).toFixed(1)}" r="${(ir * 0.55).toFixed(1)}" fill="${COLORS.pupil}"/>`;
        figure += `<circle cx="${(ex + lookX - 2.4).toFixed(1)}" cy="${(ey - 3).toFixed(1)}" r="${(ir * 0.32).toFixed(1)}" fill="#fff"/>`;
      }
      if (pulling) { // determined brows
        figure += `<path d="M${(ex - 11).toFixed(1)},${(ey - 13 + side * 2).toFixed(1)} L${(ex + 11).toFixed(1)},${(ey - 13 - side * 2).toFixed(1)}" stroke="${COLORS.dark}" stroke-width="3" stroke-linecap="round"/>`;
      }
    }
    // cheeks and mouth: "o" while being pulled, gritted while tugging, smile when done
    figure += `<ellipse cx="${(cx - 25).toFixed(1)}" cy="${(cy + 13).toFixed(1)}" rx="5" ry="3" fill="${COLORS.cheek}" opacity="0.65"/>`;
    figure += `<ellipse cx="${(cx + 25).toFixed(1)}" cy="${(cy + 13).toFixed(1)}" rx="5" ry="3" fill="${COLORS.cheek}" opacity="0.65"/>`;
    const my = cy + 19;
    figure += mode === 'holding'
      ? `<ellipse cx="${cx.toFixed(1)}" cy="${(my + 1).toFixed(1)}" rx="3.6" ry="4.4" fill="${COLORS.dark}"/>`
      : pulling
        ? `<path d="M${(cx - 7).toFixed(1)},${my.toFixed(1)} h14" stroke="${COLORS.dark}" stroke-width="2.6" stroke-linecap="round"/>`
        : `<path d="M${(cx - 7).toFixed(1)},${(my - 1).toFixed(1)} q7,7 14,0" fill="none" stroke="${COLORS.dark}" stroke-width="2.6" stroke-linecap="round"/>`;
    figure += `</g>`;

    body.innerHTML = out + scaled + figure + '</g>';
    svg.style.opacity = String(Math.min(enter * 1.4, 1) * (1 - ease(leaving)));
  }

  // ---------- animation loop (runs only while the octopus is visible) ----------
  function loop(now) {
    frame = 0;
    if (mode === 'off') return;
    if (mode === 'tugging' && tug) {
      const k = reducedMotion ? 1 : clamp01((now - tug.t0) / tug.dur);
      setTransition(tug.from + (tug.to - tug.from) * ease(k));   // moves divider + island this frame
      if (k >= 1) { tug = null; setMode('done', now); }
    }
    if (mode === 'done' && now - modeAt > EXIT_DELAY_MS) setMode('leaving', now);
    if (mode === 'leaving' && now - modeAt > EXIT_MS) { stop(); return; }
    draw(now);
    frame = requestAnimationFrame(loop);
  }
  function setMode(m, now = performance.now()) { mode = m; modeAt = now; }
  function run() { if (!frame) frame = requestAnimationFrame(loop); }
  function stop() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0; mode = 'off'; tug = null; anchor = null;
    body.innerHTML = '';
    svg.style.opacity = '0';
    divider.classList.remove('is-held');
  }

  // ---------- API ----------
  return {
    /** Pointer went down on the handle: remember where the drag starts. */
    grab() {
      if (mode === 'tugging' || mode === 'done' || mode === 'leaving') {
        // the user takes over mid-tug: keep the octopus holding from here
        tug = null;
        if (anchor) { setMode('holding'); start = Math.max(start, getTransition()); return; }
      }
      start = getTransition();
    },
    /** The user moved the divider: appear once it has gone left of the start. */
    moved() {
      const now = performance.now();
      if (mode === 'off' && getTransition() < start - START_THRESHOLD) {
        const hp = handlePoint();
        // head to the right of where the handle was when the drag began
        anchor = { x: Math.min(start * hp.w + 140, hp.w - 70), y: Math.min(hp.y + 56, hp.h - 110) };
        shownAt = now; setMode('holding', now);
        divider.classList.add('is-held');
        nextBlink = now + 1500;
        run();
      }
    },
    /** Pointer released: tug the divider back to where the drag started. */
    release() {
      if (mode !== 'holding') return;
      const from = getTransition();
      if (from >= start - 0.001) { setMode('done'); return; }
      tug = { from, to: start, t0: performance.now(), dur: 520 + 900 * (start - from) };
      setMode('tugging');
      run();
    },
    /** Landing page hidden or reset. */
    hide: stop,
    get active() { return mode !== 'off'; },
  };
}
