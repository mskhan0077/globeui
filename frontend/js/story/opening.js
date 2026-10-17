/* Opening sequence shown before the globe, from BlenderEarth (~/BlueGrid/UIUX/BlenderEarth):
     1. intro: 2.6 s logo reveal (Skip intro button)
     2. landing: the day/night island with a draggable divider
   "Explore Blue Grid", or dragging the divider to OPENING.exitAt (90% of the way right),
   fades the landing out to the globe. A [data-opening-exit="<id>"] link would also fly
   the globe to that region/place.

   History: the landing is its own entry ({ opening: 'landing' }) and exploring pushes
   the globe's ({ opening: 'globe' }), so the browser's Back from the globe (once out
   of any zoomed-in places) returns to the landing, without replaying the intro, and
   Forward goes to the globe again.

   It plays on load only when index.html's head script added .has-opening to <html>
   (a fresh visit without a #place in the URL). Markup: #opening in index.html;
   styles: css/opening.css.

   goTo(id): flies the globe to a region/place id once the globe is ready. */
import { OPENING } from '../config.js';
import { createOctopus } from './octopus.js';

export function initOpening(root, { goTo }) {
  if (!root) return;
  const html = document.documentElement;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const intro = root.querySelector('.intro');
  const story = root.querySelector('.story');
  const stage = root.querySelector('.story-visual');
  const sceneHost = root.querySelector('.story-scene');
  const divider = root.querySelector('.scene-divider');
  const handle = divider.querySelector('button');
  let transition = 0.5; // divider position: share of the scene shown in daylight
  // Violet octopus that tugs the divider back right whenever it's slid left (octopus.js)
  const octopus = createOctopus(stage, handle, { setTransition: (v) => setTransition(v), getTransition: () => transition });
  let scene = null;     // Promise of the island scene while the landing is showing
  let introTimer = 0;
  let fadeTimer = 0;

  // ---------- island scene (Three.js), created while shown, freed when hidden ----------
  function startScene() {
    scene ??= import('./island-scene.js')
      .then(({ createIslandScene }) => createIslandScene(sceneHost, transition))
      .catch((err) => { console.warn('Island scene unavailable:', err); return null; });
  }
  function stopScene() {
    scene?.then((s) => s?.dispose());
    scene = null;
  }

  // ---------- intro ----------
  function playIntro() {
    intro.hidden = false;
    story.hidden = true;
    introTimer = window.setTimeout(showLanding, reducedMotion ? 200 : OPENING.introMs);
    startScene(); // load the island while the intro plays
  }
  root.querySelector('.intro-skip').addEventListener('click', () => showLanding());

  // ---------- landing ----------
  function showLanding() {
    octopus.hide();
    window.clearTimeout(introTimer);
    window.clearTimeout(fadeTimer);
    introTimer = fadeTimer = 0;
    root.classList.remove('is-leaving');
    html.classList.add('has-opening', 'opening-story'); // ribbon above the island, without links
    story.hidden = false;
    if (!intro.hidden) {
      intro.classList.add('is-leaving');
      window.setTimeout(() => { intro.hidden = true; intro.classList.remove('is-leaving'); }, reducedMotion ? 0 : 500);
    }
    setTransition(0.5); // always arrive with the divider centred, and the hint showing
    root.classList.remove('has-slid');
    startScene();
    if (history.state?.opening !== 'landing') history.replaceState({ ...history.state, opening: 'landing' }, '');
  }

  function hideLanding() {
    octopus.hide();
    window.clearTimeout(introTimer);
    introTimer = 0;
    root.classList.add('is-leaving');
    html.classList.remove('has-opening'); // menu-bar links and help box come back
    fadeTimer = window.setTimeout(() => {
      fadeTimer = 0;
      html.classList.remove('opening-story');
      root.classList.remove('is-leaving'); // stays hidden: display needs .has-opening
      intro.hidden = true;
      stopScene();
    }, reducedMotion ? 0 : OPENING.fadeMs);
  }

  const isShowing = () => html.classList.contains('has-opening');

  // ---------- day/night divider ----------
  function setTransition(value) {
    transition = Math.min(1, Math.max(0, value));
    divider.style.left = `${transition * 100}%`;
    const pct = Math.round(transition * 100);
    handle.setAttribute('aria-valuenow', pct);
    handle.setAttribute('aria-valuetext', `${pct} percent renewable daylight`);
    scene?.then((s) => s?.setTransition(transition));
    if (transition >= OPENING.exitAt && isShowing() && !fadeTimer) exploreGlobe();
  }
  function drag(event) {
    if (!handle.hasPointerCapture(event.pointerId)) return;
    if (!isShowing() || fadeTimer) return; // leaving: the stage is fading out or already hidden
    const bounds = stage.getBoundingClientRect();
    setTransition((event.clientX - bounds.left) / bounds.width);
    octopus.moved();
  }
  handle.addEventListener('pointerdown', (event) => {
    root.classList.add('has-slid'); // hide the "slide right" hint
    handle.setPointerCapture(event.pointerId);
    octopus.grab();                 // remembers where the drag starts
    drag(event);
  });
  handle.addEventListener('pointermove', drag);
  const letGo = (event) => {
    if (handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);
    octopus.release();              // tugs back to the drag's start if it went left
  };
  handle.addEventListener('pointerup', letGo);
  handle.addEventListener('pointercancel', letGo);
  // Keys: a run of presses counts as one drag; the octopus tugs once they pause.
  let keyRun = 0;
  handle.addEventListener('keydown', (event) => {
    const keys = { ArrowLeft: transition - 0.02, ArrowRight: transition + 0.02, Home: 0, End: 1 };
    if (!(event.key in keys)) return;
    event.preventDefault();
    root.classList.add('has-slid');
    if (!keyRun) octopus.grab();
    clearTimeout(keyRun);
    setTransition(keys[event.key]);
    octopus.moved();
    keyRun = setTimeout(() => { keyRun = 0; octopus.release(); }, 600);
  });
  setTransition(transition);

  // ---------- to the globe, and back ----------
  function exploreGlobe(placeId = null) {
    history.pushState({ id: null, opening: 'globe' }, '', location.pathname + location.search);
    hideLanding();
    if (placeId) goTo(placeId);
  }
  root.querySelectorAll('[data-opening-exit]').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      exploreGlobe(link.dataset.openingExit || null);
    });
  });

  window.addEventListener('popstate', ({ state }) => {
    if (state?.opening === 'landing') { if (!isShowing() || fadeTimer) showLanding(); }
    else if (isShowing()) hideLanding();
  });

  // On load: the head script decides; a reload of the landing entry skips the intro.
  if (isShowing()) {
    if (history.state?.opening === 'landing') showLanding();
    else playIntro();
  }
}
