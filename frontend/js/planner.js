import { API_BASE_URL, PLANNER_URL } from './config.js';

// Shows the BlueGrid planner (backend page /planner, embedded with a transparent
// background) over the translucent overlay once the camera arrives at a circled
// place, preselected for that island. Places the dataset doesn't cover get a
// short message instead. Picking another island in the planner's dropdown flies
// the globe to that island behind it, keeping the planner and its inputs as they are.

let islandsPromise = null;
function islands() {
  islandsPromise ??= fetch(`${API_BASE_URL}/islands`)
    .then((res) => res.json())
    .then((body) => body.islands)
    .catch((err) => {
      islandsPromise = null; // retry next time, e.g. once the backend is started
      throw err;
    });
  return islandsPromise;
}

export function createPlanner(overlay) {
  const frame = document.createElement('div');
  frame.className = 'planner-frame';
  frame.innerHTML = `
    <button type="button" class="planner-frame__close" aria-label="Close planner">×</button>
    <p class="planner-frame__message" hidden></p>`;
  overlay.append(frame);

  const message = frame.querySelector('.planner-frame__message');
  let parentId = null;
  let session = 0; // bumped on every open/leave so a slow island lookup can't open a stale page

  const clear = () => {
    frame.querySelector('iframe')?.remove();
    message.hidden = true;
  };

  const showMessage = (text) => {
    clear();
    message.textContent = text;
    message.hidden = false;
  };

  async function open({ name, parent }) {
    const current = ++session;
    parentId = parent;
    clear();

    let known;
    try {
      known = await islands();
    } catch {
      if (current === session) {
        showMessage('The planner backend isn’t running. Start it with “cd backend && uv run flask --app run:app run” and open http://localhost:5000.');
      }
      return;
    }
    if (current !== session) return;
    if (!known.includes(name)) {
      showMessage(`There’s no resource or cost data for ${name} yet, so it can’t be planned.`);
      return;
    }

    const iframe = document.createElement('iframe');
    iframe.title = `BlueGrid planner – ${name}`;
    iframe.src = `${PLANNER_URL}?embed=1&island=${encodeURIComponent(name)}`;
    frame.append(iframe);
  }

  // The embedded planner reports dropdown changes with postMessage (see
  // backend/app/static/js/charts.js); move the globe there without reloading it.
  window.addEventListener('message', (event) => {
    const iframe = frame.querySelector('iframe');
    if (event.origin !== location.origin || !iframe || event.source !== iframe.contentWindow) return;
    if (event.data?.type !== 'bluegrid:island') return;
    window.dispatchEvent(new CustomEvent('globe:navigate', { detail: { name: event.data.name, via: 'planner' } }));
  });

  frame.querySelector('.planner-frame__close').addEventListener('click', () => {
    window.dispatchEvent(new CustomEvent('globe:navigate', { detail: { id: parentId } }));
  });

  window.addEventListener('globe:arrive', ({ detail }) => {
    if (!detail.isLeafPlace) return;
    if (detail.via === 'planner') parentId = detail.parent; // planner already shows this island
    else open(detail);
  });
  window.addEventListener('globe:leave', ({ detail }) => {
    if (detail?.via === 'planner') return; // flying to the island picked in the planner
    session++;
    clear(); // stop the old page (and any optimize request it was waiting on)
  });
}
