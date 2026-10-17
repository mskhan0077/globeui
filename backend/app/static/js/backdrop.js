/* Standalone planner page: a live, blurred globe behind the glass panels, showing
   the selected place. Picking another place in the dropdown flies the globe there,
   as on the globe page. Reuses the globe's own modules (served by Flask from
   frontend/): camera setup, imagery and the place list with zoom heights.
   Needs #backdrop, #mapCredits, #island and window.BLUEGRID.places (fallback coordinates).
   Pages without a place dropdown (e.g. /about) get the slowly spinning globe instead. */
import { createGlobe, toCartesian } from "/js/globe.js";
import { loadPlaces } from "/js/markers.js";
import { DEFAULT_PLACE_ZOOM_HEIGHT, ZOOM_DURATION_MS } from "/js/config.js";

const backdrop = document.getElementById("backdrop");
const select = document.getElementById("island");
const viewer = backdrop && createGlobe(backdrop, document.getElementById("mapCredits"));

if (viewer && !select) backdrop.classList.add("is-loaded"); // spinning whole globe

if (viewer && select) {
  viewer.autoRotate = false; // the camera only moves when the place changes

  // Globe place list first (it knows each place's zoom height); dataset coordinates otherwise.
  const places = await loadPlaces().catch(() => []);
  const fallback = window.BLUEGRID?.places || {};
  const viewFor = (name) => {
    const place = places.find((p) => p.name === name);
    if (place) return place.view;
    const [lat, lng] = fallback[name] || [];
    return lat == null ? null : { lat, lng, height: DEFAULT_PLACE_ZOOM_HEIGHT };
  };

  const start = viewFor(select.value);
  if (start) viewer.camera.setView({ destination: toCartesian(start) });
  backdrop.classList.add("is-loaded");

  select.addEventListener("change", () => {
    const view = viewFor(select.value);
    if (view) viewer.camera.flyTo({ destination: toCartesian(view), duration: ZOOM_DURATION_MS / 1000 });
  });
}
