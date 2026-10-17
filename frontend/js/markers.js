import { DEFAULT_PLACE_ZOOM_HEIGHT, MARKER_STYLE, PLACE_FILES } from './config.js';

// Loads every place from PLACE_FILES and gives each one its camera view.
export async function loadPlaces() {
  const files = await Promise.all(
    PLACE_FILES.map(async (url) => (await (await fetch(url)).json()).places)
  );
  return files.flat().map((place) => ({
    ...place,
    view: { lat: place.lat, lng: place.lng, height: place.zoomHeight ?? DEFAULT_PLACE_ZOOM_HEIGHT },
  }));
}

// Draws a circle with the place's name for each place; `isShown(place)` is
// checked every frame to decide which are visible (and none show once the
// camera is further away than MARKER_STYLE.hideBeyond). Returns
// `markerAt(position)`, which gives the place under a screen position (circle
// or name, or null), and `setHovered(place)` to enlarge the one under the cursor.
export function addMarkers(viewer, places, isShown) {
  const fill = Cesium.Color.fromCssColorString(MARKER_STYLE.fill);
  const outline = Cesium.Color.fromCssColorString(MARKER_STYLE.outline);
  const labelColor = Cesium.Color.fromCssColorString(MARKER_STYLE.labelColor);
  const labelOutline = Cesium.Color.fromCssColorString(MARKER_STYLE.labelOutline);
  const inRange = new Cesium.DistanceDisplayCondition(0, MARKER_STYLE.hideBeyond);
  let hovered = null;

  const entities = places.map((place) => {
    const show = new Cesium.CallbackProperty(() => isShown(place), false);
    return viewer.entities.add({
      id: `marker-${place.id}`,
      name: place.name,
      position: Cesium.Cartesian3.fromDegrees(place.lng, place.lat),
      point: {
        show,
        pixelSize: new Cesium.CallbackProperty(
          () => (hovered === place ? MARKER_STYLE.hoverPixelSize : MARKER_STYLE.pixelSize),
          false
        ),
        color: fill,
        outlineColor: outline,
        outlineWidth: MARKER_STYLE.outlineWidth,
        distanceDisplayCondition: inRange,
        disableDepthTestDistance: Number.POSITIVE_INFINITY, // never hidden behind terrain
      },
      label: {
        show,
        text: place.name,
        font: MARKER_STYLE.labelFont,
        fillColor: labelColor,
        outlineColor: labelOutline,
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        horizontalOrigin: Cesium.HorizontalOrigin.LEFT,
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        pixelOffset: new Cesium.Cartesian2(MARKER_STYLE.labelOffsetX, 0),
        distanceDisplayCondition: inRange,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
  });

  const markerAt = (position) => {
    const picked = viewer.scene.pick(position);
    const index = entities.indexOf(picked?.id);
    return index >= 0 ? places[index] : null;
  };

  const setHovered = (place) => {
    hovered = place;
  };

  return { markerAt, setHovered };
}
