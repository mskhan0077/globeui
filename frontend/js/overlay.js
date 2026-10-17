// Translucent layer over the map that fades in once the camera arrives at a
// circled place with nothing inside it (an island or city, not an atoll) and
// fades out as soon as the camera moves on. The place stays visible behind it.
// The layer is the container for that place's content. Moves made from the
// planner itself (via: 'planner', e.g. its island dropdown) keep it showing.
export function createPlaceOverlay(element) {
  window.addEventListener('globe:leave', ({ detail }) => {
    if (detail?.via === 'planner') return;
    element.classList.remove('is-visible');
    element.setAttribute('aria-hidden', 'true');
    delete element.dataset.place;
  });

  window.addEventListener('globe:arrive', ({ detail }) => {
    if (!detail.isLeafPlace) return;
    element.dataset.place = detail.id;
    element.classList.add('is-visible');
    element.setAttribute('aria-hidden', 'false');
  });
}
