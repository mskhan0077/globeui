/* "Why renewables" speech bubbles that come out of the Earth, styled like the "How to
   use" box (css/facts.css): each bubble sits just off the globe's right edge and a
   curved tail runs from it to a point on the globe's outline. FACTS (config.js) go top to bottom, at FACT_BUBBLES.angles.

   The globe's on-screen circle is worked out from the Cesium camera after every render,
   so the bubbles follow zoom and window size. They hide while the globe is zoomed in
   (globe:leave / globe:arrive), when there's no room beside the globe, and on small
   screens (css/facts.css). */
import { API_BASE_URL, FACTS, FACT_BUBBLES } from './config.js';

const EARTH_RADIUS_M = 6_378_137; // WGS84 equatorial radius
const BUBBLE_RADIUS = 16;          // px, corner radius (as the help box; css/facts.css)
const escape = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

// One closed outline for the bubble and its tail, in the bubble's own coordinates
// (w × h box, top-left at 0,0), so the fill and the thin edge run around both with no
// seam where the tail joins: a rounded rectangle whose left side opens into a curved
// wedge that reaches the tip (tx, ty) on the globe.
function bubbleOutline(w, h, tx, ty) {
  const r = Math.min(BUBBLE_RADIUS, w / 2, h / 2);
  const my = h / 2;
  const b = Math.min(FACT_BUBBLES.tailBase / 2, my - r); // half the tail's base
  const cx = tx * 0.45; // controls: leave the bubble level, then bend to the tip
  return [
    `M ${r} 0 H ${w - r} A ${r} ${r} 0 0 1 ${w} ${r}`,              // top, top-right corner
    `V ${h - r} A ${r} ${r} 0 0 1 ${w - r} ${h}`,                   // right, bottom-right
    `H ${r} A ${r} ${r} 0 0 1 0 ${h - r}`,                          // bottom, bottom-left
    `V ${my + b} Q ${cx} ${my + b * 0.6} ${tx} ${ty}`,              // left side, out along the tail…
    `Q ${cx} ${my - b * 0.6} 0 ${my - b}`,                          // …to the tip and back
    `V ${r} A ${r} ${r} 0 0 1 ${r} 0 Z`,                            // left, top-left corner
  ].join(' ');
}

// Text with {key} / {key1,key2} placeholders → escaped HTML with numbered citations,
// e.g. "… [3, 4]", each linking to its entry on the References page (new tab).
// Without the numbers yet, placeholders are simply left out.
function withCitations(text, numbers) {
  return String(text).split(/(\s?\{[^}]+\})/).map((part) => {
    const m = part.match(/^\s?\{([^}]+)\}$/);
    if (!m) return escape(part);
    const ns = [...new Set(m[1].split(',').map((k) => numbers?.[k.trim()]).filter(Boolean))].sort((a, b) => a - b);
    if (!ns.length) return '';
    return ` <span class="fact-bubble__cite">[${ns.map((n) =>
      `<a href="/references#ref-${n}" target="_blank" rel="noopener">${n}</a>`).join(', ')}]</span>`;
  }).join('');
}

export function createFactCards(container, viewer) {
  if (!container || !viewer) return;
  container.innerHTML = FACTS.map((f) => `
    <figure class="fact-bubble">
      <svg class="fact-bubble__outline" aria-hidden="true"><path class="fact-bubble__shape"/></svg>
      <p class="fact-bubble__title">${escape(f.title)}</p>
      <p class="fact-bubble__text">${withCitations(f.text, null)}</p>
    </figure>`).join('');
  const bubbles = [...container.querySelectorAll('.fact-bubble')];

  // Swap the {key} placeholders for numbered citations once the numbers are in.
  fetch(`${API_BASE_URL}/references`)
    .then((r) => r.json())
    .then(({ numbers }) => bubbles.forEach((el, i) => {
      el.querySelector('.fact-bubble__text').innerHTML = withCitations(FACTS[i].text, numbers);
      last = ''; // bubble heights may change: lay out again
    }))
    .catch(() => {}); // no citations if the list is unavailable

  // ---------- where is the globe on screen? ----------
  // Plain perspective projection of the Earth's centre and radius from the camera's view
  // matrix. (Cesium's SceneTransforms isn't used: called from postRender while zoomed in,
  // it can break the render loop.)
  const scene = viewer.scene;
  function globeCircle() {
    const camera = viewer.camera;
    const view = camera.viewMatrix;                      // world → camera (column-major)
    const ex = view[12], ey = view[13], ez = view[14];   // Earth's centre in camera space
    const fovy = camera.frustum.fovy;
    const w = scene.canvas.clientWidth, h = scene.canvas.clientHeight;
    const distance = Math.hypot(ex, ey, ez);
    if (!(ez < 0) || !fovy || !(distance > EARTH_RADIUS_M)) return null; // behind, or inside
    const f = (h / 2) / Math.tan(fovy / 2);              // focal length in CSS px
    const circle = {
      x: w / 2 + (f * ex) / -ez,
      y: h / 2 - (f * ey) / -ez,
      r: f * Math.tan(Math.asin(EARTH_RADIUS_M / distance)),
    };
    return Object.values(circle).every(Number.isFinite) ? circle : null;
  }

  // ---------- place each bubble and draw its tail ----------
  let last = '';
  function layout() {
    const circle = globeCircle();
    const key = circle ? `${circle.x.toFixed(1)},${circle.y.toFixed(1)},${circle.r.toFixed(1)},${innerWidth},${innerHeight}` : 'none';
    if (key === last) return; // nothing moved (the globe spinning doesn't change its outline)
    last = key;
    if (!circle) { container.classList.add('no-room'); return; }

    const { gap, spread, margin, maxWidth, minWidth } = FACT_BUBBLES;
    const minTail = 36; // px: the shortest tail that still reads as coming from the globe
    const space = 14; // px between bubbles
    const top = (parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--menubar-bottom')) || 76) + margin;
    const bottom = innerHeight - 30; // above the imagery credit
    const right = innerWidth - margin;

    // Ideal spots: a gap out from the outline at each angle, spread out vertically.
    const items = bubbles
      .map((el, i) => ({ el, a: (FACT_BUBBLES.angles[i] ?? 0) * Math.PI / 180 }))
      .filter(({ el }) => getComputedStyle(el).display !== 'none')
      .map(({ el, a }) => {
        const edgeX = circle.x + circle.r * Math.cos(a); // the globe's outline at this angle
        // As wide as fits between the outline (plus a short tail) and the screen edge.
        const room = right - (edgeX + minTail);
        el.style.width = `${Math.max(minWidth, Math.min(maxWidth, room))}px`;
        const w = el.offsetWidth, h = el.offsetHeight;
        const tip = { x: circle.x + (circle.r - 4) * Math.cos(a), y: circle.y + (circle.r - 4) * Math.sin(a) };
        const left = Math.min(edgeX + gap, right - w);
        return { el, w, h, tip, left, y: circle.y + circle.r * Math.sin(a) * spread - h / 2 };
      });

    // Keep them on screen without overlapping: push down from the top, then up from the bottom.
    let edge = top;
    for (const it of items) { it.y = Math.max(it.y, edge); edge = it.y + it.h + space; }
    edge = bottom;
    for (const it of [...items].reverse()) { it.y = Math.min(it.y, edge - it.h); edge = it.y - space; }
    const fits = items.length > 0 && items[0].y >= top - 0.5 && items.every((it) => it.left - it.tip.x >= 28);
    // (too little room beside the globe leaves the tail shorter than 28 px: hide them all)

    for (const { el, h, tip, left, y } of items) {
      el.style.left = `${left}px`;
      el.style.top = `${y}px`;
      el.querySelector('.fact-bubble__shape').setAttribute('d', bubbleOutline(el.offsetWidth, h, tip.x - left, tip.y - y));
    }
    container.classList.toggle('no-room', !fits);
  }
  // Runs inside Cesium's render loop, where an exception would stop the globe rendering:
  // never let a bubble problem do that.
  scene.postRender.addEventListener(() => {
    try { layout(); } catch (err) { container.classList.add('no-room'); console.warn('Fact bubbles:', err); }
  });
  window.addEventListener('resize', () => { last = ''; });

  // Only on the zoomed-out globe: hide while flying in or looking at a region/place.
  const setHidden = (hidden) => container.classList.toggle('is-hidden', hidden);
  setHidden(Boolean(location.hash));
  window.addEventListener('globe:leave', () => setHidden(true));
  window.addEventListener('globe:arrive', ({ detail }) => setHidden(detail?.id != null));
}
