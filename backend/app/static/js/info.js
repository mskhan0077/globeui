/* (i) info buttons. Two kinds:
     data-tech="<technology>"  parameters of that technology (via /api/tech)
     data-info="<key>"         an explanation from info-content.js (charts, KPIs), which can
                               quote live finance parameters (/api/finance)
   The box shows on hover/focus, is pinned by click or tap, and closes with Esc or
   a click elsewhere. Use: window.BlueGrid.info.attach(container) after rendering buttons. */
(() => {
  // Cached JSON lookups; a failed one is retried next time.
  function cached(url, pick) {
    let promise = null;
    return () =>
      (promise ??= fetch(url)
        .then((r) => r.json())
        .then(pick)
        .catch((err) => { promise = null; throw err; }));
  }
  const loadTech = cached("/api/tech", (j) => j.tech);
  const loadFinance = cached("/api/finance", (j) => j.finance);
  const loadCitations = cached("/api/references", (j) => j.citations);

  const escape = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
  const inr = (x) => "₹" + Number(x).toLocaleString("en-IN", { maximumFractionDigits: 0 });
  const pct = (x, d = 1) => `${(Number(x) * 100).toFixed(d)}%`;
  const text = (x) => (x == null || x === "" ? "–" : String(x));

  // ---------- content ----------

  function techRows(name, p) {
    const unit = name === "BESS" ? "kWh" : "kW";
    return [
      ["Typical unit", text(p.typical_unit_size)],
      ["CAPEX (island-adjusted)", p.capex_island_INR == null ? "–" : `${inr(p.capex_island_INR)} / ${unit}`],
      ["OPEX", p.opex_INR_per_unit_yr == null ? "–" : `${inr(p.opex_INR_per_unit_yr)} / ${unit} / yr`],
      ["OPEX share of CAPEX", p.opex_pct_of_capex == null ? "–" : `${pct(p.opex_pct_of_capex)} / yr`],
      ["Lifetime", p.lifetime_yr == null ? "–" : `${Number(p.lifetime_yr)} years`],
      ["Degradation", p.degradation_per_yr == null ? "–" : `${pct(p.degradation_per_yr)} / yr`],
      ["Availability", p.availability == null ? "–" : pct(p.availability, 0)],
      ["Lifecycle emissions", isFinite(p.lifecycle_gCO2_per_kWh) ? `${p.lifecycle_gCO2_per_kWh} gCO₂/kWh` : text(p.lifecycle_gCO2_per_kWh)],
      ["Technology readiness (TRL)", text(p.TRL)],
    ];
  }

  async function techContent(name) {
    const p = (await loadTech())[name];
    const body = p
      ? `<dl class="info-box__list">${techRows(name, p).map(([k, v]) =>
          `<dt>${escape(k)}</dt><dd>${escape(v)}</dd>`).join("")}</dl>`
      : `<p class="info-box__muted">No parameters found for this technology.</p>`;
    return { title: name, html: body };
  }

  async function explanationContent(key) {
    const entry = window.BlueGrid.infoContent?.[key];
    if (!entry) return { title: "Info", html: `<p class="info-box__muted">No description yet.</p>` };
    const finance = entry.needsFinance ? await loadFinance() : {};
    const ctx = { finance, defaults: window.BLUEGRID?.defaults || {}, fmt: { inr, pct } };
    return { title: entry.title, html: entry.html(ctx), refs: entry.refs };
  }

  // ---------- the box ----------

  // One shared box, moved next to whichever button is active.
  const box = document.createElement("div");
  box.className = "info-box";
  box.id = "info-box";
  box.setAttribute("role", "dialog");
  box.hidden = true;
  let current = null;   // button the box belongs to
  let pinned = false;   // opened by click (stays until closed)

  function place(button) {
    const r = button.getBoundingClientRect();
    const w = box.offsetWidth, h = box.offsetHeight, pad = 8;
    const left = Math.min(r.left, window.innerWidth - w - pad);
    let top = r.bottom + 8;
    if (top + h > window.innerHeight - pad) top = Math.max(pad, r.top - h - 8); // flip above if no room below
    box.style.left = `${Math.max(pad, left)}px`;
    box.style.top = `${top}px`;
  }

  // "References: (Short et al., 1995; EIA, 2025)", the words linking to each entry on the
  // References page (new tab, so the planner stays as it is).
  function references(keys, citations) {
    const links = (keys || []).map((k) => citations?.[k]).filter(Boolean)
      .map(({ label, href }) => `<a href="${escape(href)}" target="_blank" rel="noopener">${escape(label)}</a>`);
    return links.length ? `<p class="info-box__refs">References: (${links.join("; ")})</p>` : "";
  }

  function render({ title, html, refs }, citations) {
    box.innerHTML = `<p class="info-box__title">${escape(title)}</p>${html}` + references(refs, citations);
  }

  async function open(button, pin) {
    current?.setAttribute("aria-expanded", "false");
    current = button;
    pinned = pin;
    button.setAttribute("aria-expanded", "true");
    const label = button.dataset.tech || button.getAttribute("aria-label") || "Info";
    box.setAttribute("aria-label", label);
    render({ title: button.dataset.tech || "", html: `<p class="info-box__muted">Loading…</p>` });
    box.hidden = false;
    place(button);
    try {
      const content = button.dataset.tech ? await techContent(button.dataset.tech) : await explanationContent(button.dataset.info);
      const citations = content.refs ? await loadCitations().catch(() => null) : null; // none if unavailable
      if (current === button) render(content, citations);
    } catch {
      if (current === button) render({ title: label, html: `<p class="info-box__muted">Couldn’t load this information.</p>` });
    }
    if (current === button) place(button);
  }

  function close() {
    current?.setAttribute("aria-expanded", "false");
    current = null;
    pinned = false;
    box.hidden = true;
  }

  function attach(container) {
    container.querySelectorAll("[data-tech], [data-info]").forEach((button) => {
      if (button.dataset.infoWired) return;
      button.dataset.infoWired = "1";
      button.setAttribute("aria-haspopup", "dialog");
      button.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-controls", box.id);
      button.addEventListener("mouseenter", () => { if (!pinned) open(button, false); });
      button.addEventListener("mouseleave", () => { if (!pinned && current === button) close(); });
      button.addEventListener("focus", () => { if (!pinned) open(button, false); });
      button.addEventListener("blur", () => { if (!pinned && current === button) close(); });
      button.addEventListener("click", (e) => {
        e.preventDefault();
        if (pinned && current === button) close();
        else open(button, true);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.body.append(box);
    attach(document); // buttons already in the page (e.g. chart headings)
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && current) close(); });
  document.addEventListener("click", (e) => {
    if (pinned && !box.contains(e.target) && !e.target.closest("[data-tech], [data-info]")) close();
  });
  window.addEventListener("scroll", () => current && place(current), true);
  window.addEventListener("resize", () => current && place(current));

  window.BlueGrid = window.BlueGrid || {};
  window.BlueGrid.info = { attach, close };
})();
