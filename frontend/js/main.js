import { createGlobe } from './globe.js';
import { addClickableCountries } from './countries.js';
import { createPlaceOverlay } from './overlay.js';
import { createPlanner } from './planner.js';
import { initHelp } from './help.js';
import { createFactCards } from './facts.js';
import { initOpening } from './story/opening.js';

const overlay = document.getElementById('placeOverlay');
createPlaceOverlay(overlay);
createPlanner(overlay);
initHelp(document.getElementById('help'));
const globe = createGlobe(document.getElementById('globeViz'), document.getElementById('mapCredits'));
const globeReady = addClickableCountries(globe);
createFactCards(document.getElementById('facts'), globe); // speech bubbles from the Earth

// Intro + day/night island before the globe (fresh visits, and Back from the globe)
initOpening(document.getElementById('opening'), {
  goTo: (id) => globeReady.then(() => window.dispatchEvent(new CustomEvent('globe:navigate', { detail: { id } }))),
});
