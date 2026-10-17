import { GLOBE } from './config.js';

// `Cesium` is the global provided by the CesiumJS script tag in index.html.
// Map credits are rendered into `creditContainer` (outside the map, so they
// stay above any overlay).
export function createGlobe(container, creditContainer) {
  const imagery = new Cesium.UrlTemplateImageryProvider({
    url: GLOBE.imageryUrl,
    credit: new Cesium.Credit(GLOBE.imageryCredit, true), // true = always shown on screen
    maximumLevel: GLOBE.imageryMaxLevel,
  });

  const viewer = new Cesium.Viewer(container, {
    baseLayer: new Cesium.ImageryLayer(imagery),
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    animation: false,
    timeline: false,
    fullscreenButton: false,
    infoBox: false,
    selectionIndicator: false,
    creditContainer,
  });

  const { scene } = viewer;
  scene.skyBox.show = false;
  scene.sun.show = false;
  scene.moon.show = false;
  scene.backgroundColor = Cesium.Color.BLACK;
  scene.skyAtmosphere.show = true;
  const controls = scene.screenSpaceCameraController;
  controls.enableZoom = true; // mouse wheel, right-drag and pinch
  controls.minimumZoomDistance = GLOBE.minZoomHeight;
  controls.maximumZoomDistance = GLOBE.maxZoomHeight;

  setView(viewer, GLOBE.startView);
  startAutoRotate(viewer);

  return viewer;
}

export function toCartesian({ lat, lng, height }) {
  return Cesium.Cartesian3.fromDegrees(lng, lat, height);
}

function setView(viewer, view) {
  viewer.camera.setView({ destination: toCartesian(view) });
}

// Make the earth revolve by spinning the camera around the polar axis.
// Toggle with `viewer.autoRotate = true/false`.
function startAutoRotate(viewer) {
  viewer.autoRotate = true;
  const radiansPerSecond = (2 * Math.PI) / GLOBE.rotationSecondsPerTurn;
  let last = performance.now();

  viewer.scene.preRender.addEventListener(() => {
    const now = performance.now();
    const dt = (now - last) / 1000;
    last = now;
    if (viewer.autoRotate) viewer.camera.rotate(Cesium.Cartesian3.UNIT_Z, -radiansPerSecond * dt);
  });

  // Pause the spin while the user zooms by hand; zooming back out (empty-globe
  // click or Back to the start view) turns it on again.
  const input = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
  const pause = () => (viewer.autoRotate = false);
  input.setInputAction(pause, Cesium.ScreenSpaceEventType.WHEEL);
  input.setInputAction(pause, Cesium.ScreenSpaceEventType.PINCH_START);
  input.setInputAction(pause, Cesium.ScreenSpaceEventType.RIGHT_DOWN);
}
