/* Embedded planner (/planner?embed=1 inside the globe): tells the globe page which
   island was picked in the dropdown so it can fly there (frontend/js/planner.js). */
(() => {
  if (window.parent === window) return;
  document.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("island");
    select?.addEventListener("change", () => {
      window.parent.postMessage({ type: "bluegrid:island", name: select.value }, location.origin);
    });
  });
})();
