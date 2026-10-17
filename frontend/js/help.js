// "How to use" box: starts folded on small screens, where it would cover the globe.
export function initHelp(details, smallScreen = '(max-width: 640px)') {
  if (details && window.matchMedia(smallScreen).matches) details.open = false;
}
