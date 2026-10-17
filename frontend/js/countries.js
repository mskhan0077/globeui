import { COUNTRIES_URL, EXTRA_REGIONS, GLOBE, VIEW_OVERRIDES, ZOOM_DURATION_MS } from './config.js';
import { toCartesian } from './globe.js';
import { addMarkers, loadPlaces } from './markers.js';

async function fetchFeatures(url) {
  const res = await fetch(url);
  return (await res.json()).features;
}

// Extra regions first so they win over the countries around them.
async function loadRegions() {
  const extras = await Promise.all(
    EXTRA_REGIONS.map(async (region) =>
      (await fetchFeatures(region.dataUrl)).map((f) => ({ iso: region.iso, geometry: f.geometry, view: region.view }))
    )
  );
  const countries = (await fetchFeatures(COUNTRIES_URL)).map((f) => ({
    iso: f.properties.iso,
    name: f.properties.name,
    geometry: f.geometry,
    view: VIEW_OVERRIDES[f.properties.iso] ?? null, // null = frame automatically
  }));
  return [...extras.flat(), ...countries];
}

// Rough area of a [lng, lat] ring, in square degrees corrected for latitude.
function ringArea(ring) {
  const cosLat = Math.cos(Cesium.Math.toRadians(ring[0][1]));
  let sum = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    sum += (ring[j][0] - ring[i][0]) * (ring[j][1] + ring[i][1]);
  }
  return Math.abs(sum / 2) * cosLat;
}

// Bounding box of a country's main landmasses: polygons smaller than a quarter
// of the largest (e.g. French Guiana for France) are ignored. Countries
// crossing the 180° line are measured in 0–360° longitude so the box stays tight.
function mainBounds(geometry) {
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  const areas = polygons.map(([outer]) => ringArea(outer));
  const largest = Math.max(...areas);
  const points = polygons.filter((_, i) => areas[i] >= largest / 4).flatMap(([outer]) => outer);

  const box = (lngs) => ({
    west: Math.min(...lngs),
    east: Math.max(...lngs),
    south: Math.min(...points.map((p) => p[1])),
    north: Math.max(...points.map((p) => p[1])),
  });
  const plain = box(points.map((p) => p[0]));
  if (plain.east - plain.west <= 180) return plain;
  const shifted = box(points.map((p) => (p[0] < 0 ? p[0] + 360 : p[0])));
  return shifted.east - shifted.west < plain.east - plain.west ? shifted : plain;
}

// Camera view that fits a country on screen with some margin around it.
function autoView(viewer, geometry) {
  const { west, east, south, north } = mainBounds(geometry);
  const padLng = (east - west) * 0.2;
  const padLat = (north - south) * 0.2;
  const wrap = (lng) => ((lng + 540) % 360) - 180; // back into -180..180; west > east means it crosses 180°
  const rect = Cesium.Rectangle.fromDegrees(
    wrap(west - padLng),
    Math.max(-90, south - padLat),
    wrap(east + padLng),
    Math.min(90, north + padLat)
  );
  const carto = Cesium.Cartographic.fromCartesian(viewer.camera.getRectangleCameraCoordinates(rect));
  return { lat: Cesium.Math.toDegrees(carto.latitude), lng: Cesium.Math.toDegrees(carto.longitude), height: carto.height };
}

// Standard ray-casting test; `ring` is a GeoJSON array of [lng, lat] points.
function inRing(lng, lat, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function inGeometry(lng, lat, geometry) {
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  return polygons.some(
    ([outer, ...holes]) => inRing(lng, lat, outer) && !holes.some((h) => inRing(lng, lat, h))
  );
}

// Lat/lng on the globe under a screen position, or null if pointing at space.
function pickLatLng(viewer, position) {
  const cartesian = viewer.camera.pickEllipsoid(position, viewer.scene.globe.ellipsoid);
  if (!cartesian) return null;
  const carto = Cesium.Cartographic.fromCartesian(cartesian);
  return { lat: Cesium.Math.toDegrees(carto.latitude), lng: Cesium.Math.toDegrees(carto.longitude) };
}

// Makes every country, extra region and place respond to clicks (countries
// and regions are not drawn; places are named circles); clicking one flies the
// camera to it, clicking anywhere else on the globe zooms back out and resumes
// rotation.
//
// Every view change is a browser history entry (URL hash = id, e.g. #IND or
// #kadmat), so the Back/Forward buttons retrace views and links can open
// straight onto a place.
//
// View changes are announced as window events so other UI can react:
//   'globe:leave'  – the camera starts moving away from the current view; detail = { via }
//   'globe:arrive' – the camera has arrived; detail = { id, name, parent, isLeafPlace, via }
//                    (id null = zoomed out; isLeafPlace = a circled place with
//                    nothing inside it, e.g. an island or city, not an atoll)
// and other UI can move the camera by dispatching
//   'globe:navigate' – detail = { id } or { name } (id null = zoom out), plus an
//                      optional `via` tag that is echoed in the leave/arrive
//                      events it causes; recorded in history
export async function addClickableCountries(viewer) {
  const [regions, markerPlaces] = await Promise.all([loadRegions(), loadPlaces()]);
  const duration = ZOOM_DURATION_MS / 1000;

  // Everything you can navigate to, regions and places alike, keyed by id.
  const places = new Map([
    ...regions.map((r) => [r.iso, r]),
    ...markerPlaces.map((p) => [p.id, p]),
  ]);
  const placeById = (id) => places.get(id) ?? null;
  let currentId = null;

  // Parent, grandparent, ... of a place (e.g. kalpeni → kalpeni-atoll → IND-LD).
  const ancestorsOf = (id) => {
    const ancestors = new Set();
    for (let p = placeById(id)?.parent; p && !ancestors.has(p); p = placeById(p)?.parent) ancestors.add(p);
    return ancestors;
  };

  // A place's circle shows while viewing its parent, or a sibling place.
  const isShown = (place) => {
    if (!currentId || place.id === currentId) return false;
    const currentParent = placeById(currentId)?.parent;
    return place.parent === currentId || (!!currentParent && place.parent === currentParent);
  };

  const { markerAt, setHovered } = addMarkers(viewer, markerPlaces, isShown);

  // What a click at `position` should navigate to: an id, null to zoom out, or
  // undefined to do nothing (clicked space, or an area the current place is in).
  const targetAt = (position, marker = markerAt(position)) => {
    if (marker) return marker.id;

    const point = pickLatLng(viewer, position);
    if (!point) return undefined;
    const region = regions.find((r) => inGeometry(point.lng, point.lat, r.geometry));
    if (!region) return null;
    return ancestorsOf(currentId).has(region.iso) ? undefined : region.iso;
  };

  const placeIds = new Set(markerPlaces.map((p) => p.id));
  const parentIds = new Set(markerPlaces.map((p) => p.parent));
  const announce = (type, detail) => window.dispatchEvent(new CustomEvent(type, { detail }));
  const arrived = (id, via) =>
    announce('globe:arrive', {
      id,
      name: placeById(id)?.name ?? null,
      parent: placeById(id)?.parent ?? null,
      isLeafPlace: placeIds.has(id) && !parentIds.has(id),
      via,
    });

  const zoomTo = (place, flyDuration = duration, via) => {
    viewer.autoRotate = false;
    announce('globe:leave', { via });
    const id = currentId;
    const view = place.view ?? autoView(viewer, place.geometry);
    viewer.camera.flyTo({ destination: toCartesian(view), duration: flyDuration, complete: () => arrived(id, via) });
  };

  const zoomOut = (via) => {
    announce('globe:leave', { via });
    const carto = viewer.camera.positionCartographic;
    const view = {
      lat: Cesium.Math.toDegrees(carto.latitude),
      lng: Cesium.Math.toDegrees(carto.longitude),
      height: GLOBE.startView.height,
    };
    viewer.camera.flyTo({
      destination: toCartesian(view),
      duration,
      complete: () => {
        viewer.autoRotate = true;
        arrived(null, via);
      },
    });
  };

  // Moves to the view for `id` (null = zoomed out) and records it in history.
  const navigate = (id, via) => {
    if (id === currentId) return;
    currentId = id;
    history.pushState({ id }, '', id ? `#${id}` : location.pathname + location.search);
    id ? zoomTo(placeById(id), duration, via) : zoomOut(via);
  };

  // Lock the camera while a place's planner is open, so the background only
  // moves when the planner itself asks (its dropdown); unlock on leaving.
  const controls = viewer.scene.screenSpaceCameraController;
  window.addEventListener('globe:arrive', ({ detail }) => {
    controls.enableInputs = !detail.isLeafPlace;
  });
  window.addEventListener('globe:leave', ({ detail }) => {
    if (detail?.via !== 'planner') controls.enableInputs = true;
  });

  window.addEventListener('globe:navigate', ({ detail = {} }) => {
    const id = detail.name != null ? markerPlaces.find((p) => p.name === detail.name)?.id : detail.id ?? null;
    if (id === null || placeById(id)) navigate(id, detail.via);
  });

  window.addEventListener('popstate', () => {
    const place = placeById(location.hash.slice(1));
    currentId = place ? location.hash.slice(1) : null;
    place ? zoomTo(place) : zoomOut();
  });

  // Open directly on a place when the URL has its hash (e.g. a shared link).
  const initialId = location.hash.slice(1);
  if (placeById(initialId)) {
    currentId = initialId;
    zoomTo(placeById(initialId), 0);
  }
  history.replaceState({ ...history.state, id: currentId }, ''); // keeps other keys (e.g. the opening's)

  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);

  handler.setInputAction(({ endPosition }) => {
    const marker = markerAt(endPosition);
    setHovered(marker);
    viewer.canvas.style.cursor = typeof targetAt(endPosition, marker) === 'string' ? 'pointer' : '';
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

  handler.setInputAction(({ position }) => {
    const target = targetAt(position);
    if (target !== undefined) navigate(target);
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
}
