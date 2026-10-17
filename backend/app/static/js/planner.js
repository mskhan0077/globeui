/* BlueGrid planner: sliders, API calls, KPIs, charts, ranked mixes, comparison, exports.
   Charts are drawn through window.BlueGrid.plot (theme.js). */
(() => {
  // `tech` is the technology's name in tech_params.csv, for its (i) info box.
  const SLIDERS = [
    { key: "wind_kW",   label: "Wind",           tech: "Wind" },
    { key: "solar_kWp", label: "Floating solar", tech: "Floating Solar PV" },
    { key: "otec_kW",   label: "OTEC",           tech: "OTEC" },
    { key: "wave_kW",   label: "Wave",           tech: "Wave" },
    { key: "bess_kWh",  label: "BESS",           tech: "BESS" },
  ];

  // Optimizer diversity constraints: minimum capacity of a technology as a % of the load.
  const MIX_SLIDERS = [
    { key: "min_wind_pct",  label: "Wind" },
    { key: "min_solar_pct", label: "Floating solar" },
    { key: "min_otec_pct",  label: "OTEC" },
    { key: "min_wave_pct",  label: "Wave" },
  ];
  const defaultMix = () => Object.fromEntries(
    MIX_SLIDERS.map(({ key }) => [key, Math.round((window.BLUEGRID.defaults[key] || 0) * 100)]));

  // Chart rendering (dark glass theme) lives in theme.js.
  const plot = window.BlueGrid.plot;

  const state = {
    capacities: { wind_kW: 1500, solar_kWp: 1500, otec_kW: 500, wave_kW: 0, bess_kWh: 4000 },
    lastResult: null,
    lastRunId: null,
    lastOptimize: null, // { id, island, load_kW } of the last Find optimal mix
    mix: defaultMix(),  // minimum shares for Find optimal mix, in % of the load
  };

  const els = {
    island: document.getElementById("island"),
    load: document.getElementById("load_kW"),
    sliders: document.getElementById("sliders"),
    status: document.getElementById("status"),
    kpis: document.getElementById("kpis"),
    ranked: document.getElementById("ranked"),
  };

  function buildSliders() {
    const bounds = window.BLUEGRID.defaults.bounds;
    const step = window.BLUEGRID.defaults.step;
    const html = SLIDERS.map(({ key, label, tech }) => {
      const [lo, hi] = bounds[key];
      const s = step[key];
      const v = state.capacities[key];
      return `
        <div class="slider-row">
          <div class="slider-head">
            <span id="lbl-${key}">${label} — <output id="out-${key}">${v}</output></span>
            <button type="button" class="info-btn" data-tech="${tech}" aria-label="About ${label}">i</button>
          </div>
          <input type="range" id="sl-${key}" min="${lo}" max="${hi}" step="${s}" value="${v}" aria-labelledby="lbl-${key}">
        </div>`;
    }).join("");
    els.sliders.innerHTML = html;
    window.BlueGrid.info?.attach(els.sliders);
    SLIDERS.forEach(({ key }) => {
      const el = document.getElementById("sl-" + key);
      const out = document.getElementById("out-" + key);
      el.addEventListener("input", () => {
        state.capacities[key] = Number(el.value);
        out.textContent = el.value;
      });
    });
  }

  // "Minimum share" sliders (0–100% of the load, step 5) for Find optimal mix
  function buildMixSliders() {
    const host = document.getElementById("mix-sliders");
    host.innerHTML = MIX_SLIDERS.map(({ key, label }) => `
      <div class="slider-row">
        <div class="slider-head"><span id="lbl-${key}">${label} — at least <output id="out-${key}">${state.mix[key]}</output>%</span></div>
        <input type="range" id="sl-${key}" min="0" max="100" step="5" value="${state.mix[key]}" aria-labelledby="lbl-${key}">
      </div>`).join("");
    MIX_SLIDERS.forEach(({ key }) => {
      const el = document.getElementById("sl-" + key);
      el.addEventListener("input", () => {
        state.mix[key] = Number(el.value);
        document.getElementById("out-" + key).textContent = el.value;
      });
    });
  }

  // `info` is the key of the KPI's (i) explanation in info-content.js.
  function kpiCard(label, value, sub, info) {
    const btn = info ? `<button type="button" class="info-btn" data-info="${info}" aria-label="About ${label}">i</button>` : "";
    return `<div class="kpi"><div class="kpi-label">${label}${btn}</div>
            <div class="kpi-value">${value}</div>
            <div class="kpi-sub">${sub || ""}</div></div>`;
  }

  function renderKPIs(r) {
    const e = r.econ, c = r.carbon, rel = r.reliability, a = r.annual;
    const lpsp = rel.lpsp_hourly ?? rel.lpsp_annual ?? rel.lpsp_monthly;
    const inr = (x) => x.toLocaleString("en-IN", { maximumFractionDigits: 0 });
    const num = (x, d = 2) => Number(x).toFixed(d);
    // CAPEX already includes the bulk (volume) discount; show how much it saved
    const vd = Object.values(r.volume_discount || {});
    const saving = vd.reduce((sum, d) => sum + d.list_INR - d.discounted_INR, 0);
    const capexSub = saving > 0 ? `island-adjusted, −₹${num(saving / 1e7, 2)} Cr volume discount` : "island-adjusted";
    els.kpis.innerHTML = [
      kpiCard("LCOE (RE only)", `₹${num(e.LCOE_RE_INR_per_kWh)}`, "per kWh delivered", "lcoe"),
      kpiCard("System cost", `₹${num(e.cost_of_service_INR_per_kWh)}`, "incl. diesel top-up", "cos"),
      kpiCard("Nominal rate", e.nominal_discount_rate != null ? `${num(e.nominal_discount_rate * 100)}%` : "N/A", "WACC + inflation", "nominal"),
      kpiCard("PLF vs target", `${num(r.plf_target * 100, 1)}%`, `${inr(a.delivered_kWh / 1000)} MWh served`, "plf"),
      kpiCard("LPSP", `${num(lpsp * 100)}%`, rel.lpsp_hourly != null ? "hourly" : "annual", "lpsp"),
      kpiCard("CO₂ avoided", `${inr(c.co2_avoided_t)} t`, "per year", "co2"),
      kpiCard("CAPEX", `₹${num(e.capex_INR / 1e7, 1)} Cr`, capexSub, "capex"),
      kpiCard("Unmet", `${inr(a.unmet_kWh / 1000)} MWh`, "diesel top-up", "unmet"),
    ].join("");
    window.BlueGrid.info?.close(); // its button may just have been replaced
    window.BlueGrid.info?.attach(els.kpis);
  }

  // Volume (bulk) discount per technology: list CAPEX vs discounted, from the evaluate result
  function renderDiscount(r) {
    const panel = document.getElementById("panel-discount");
    const vd = SLIDERS.map(({ key }) => (r.volume_discount || {})[key]).filter((d) => d && d.list_INR > 0);
    panel.hidden = !vd.length;
    if (!vd.length) return;
    const cr = (x) => `₹${(x / 1e7).toFixed(2)} Cr`;
    const list = vd.reduce((sum, d) => sum + d.list_INR, 0);
    const net = vd.reduce((sum, d) => sum + d.discounted_INR, 0);
    const row = (name, units, l, pct, n) =>
      `<tr><td>${name}</td><td>${units}</td><td>${cr(l)}</td><td>${(pct * 100).toFixed(1)}%</td><td>${cr(l - n)}</td><td>${cr(n)}</td></tr>`;
    document.getElementById("table-discount").innerHTML = `
      <table class="ranked-table">
        <thead><tr><th>Technology</th><th>Units bought</th><th>List CAPEX</th><th>Discount</th><th>Saving</th><th>Discounted CAPEX</th></tr></thead>
        <tbody>
          ${vd.map((d) => row(d.tech, `${d.units.toFixed(1)} × ${d.unit_size} ${d.unit_basis}`, d.list_INR, d.discount_pct, d.discounted_INR)).join("")}
          <tr class="total-row">${row("Total", "", list, 1 - net / list, net).slice(4)}
        </tbody>
      </table>`;
  }

  // Data statistics panel: (1) mean / median / spread of each source's monthly generation
  // and of the load, as in BoobWorld; (2) the place's resource (capacity factors), which
  // doesn't depend on the sliders.
  function renderStats(r) {
    const panel = document.getElementById("panel-stats");
    const labels = { wind: "Wind", solar: "Floating solar", otec: "OTEC", wave: "Wave", load: "Load" };
    const entries = Object.keys(labels).filter((k) => r.stats?.[k])       // fixed order: sources, then load
      .map((k) => [k, r.stats[k]]).filter(([k, st]) => k === "load" || st.max > 0); // skip unused sources
    panel.hidden = !entries.length;
    if (!entries.length) return;
    const line = (label, v) => `<div class="stat-row"><span>${label}</span><span>${v.toFixed(1)}</span></div>`;
    document.getElementById("stats-grid").innerHTML = entries.map(([k, st]) => `
      <div class="stat-card">
        <div class="stat-title">${labels[k] || k}</div>
        ${line("Mean", st.mean)}${line("Median", st.median)}${line("Std dev", st.std)}${line("Min", st.min)}${line("Max", st.max)}
      </div>`).join("");

    const pct = (x) => `${(x * 100).toFixed(1)}%`;
    const rows = SLIDERS.filter(({ tech }) => r.tech_scores?.[tech]).map(({ label, tech }) => {
      const t = r.tech_scores[tech];
      return `<tr><td>${label}</td><td>${pct(t.cf_annual)}</td><td>${pct(t.firmness * t.cf_annual)}</td><td>${pct(t.cf_min)}</td><td>${pct(t.cf_max)}</td></tr>`;
    }).join("");
    document.getElementById("resource-basis").textContent = r.reliability?.lpsp_hourly != null ? "hourly data" : "monthly averages";
    document.getElementById("resource-stats").innerHTML = rows ? `
      <table class="ranked-table">
        <thead><tr><th>Technology</th><th>Average</th><th>10th percentile</th><th>Lowest</th><th>Highest</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>` : "";
  }

  function renderMonthly(r) {
    const months = r.monthly.map((m) => m.month_num);
    const trace = (key, name) => ({
      x: months, y: r.monthly.map((m) => m[key] / 1000),
      name, type: "bar",
    });
    const traces = [
      trace("gen_wind_kWh", "Wind"),
      trace("gen_fpv_kWh", "FPV"),
      trace("gen_otec_kWh", "OTEC"),
      trace("gen_wave_kWh", "Wave"),
      {
        x: months, y: r.monthly.map((m) => m.load_kWh / 1000),
        name: "Load", type: "scatter", mode: "lines",
        line: { color: "#d62728", width: 2 },
      },
    ];
    // ❗ above each month whose total generation is below the load (as in BoobWorld);
    // clicking one, or the link under the chart, opens the alternatives box.
    const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const deficit = r.monthly.filter((m) => m.gen_total_kWh < m.load_kWh);
    window.BlueGrid.deficitMonths = deficit.map((m) => MONTHS[m.month_num - 1]);
    const annotations = deficit.map((m) => ({
      x: m.month_num, y: 1.06, yref: "paper", text: "❗", showarrow: false, font: { size: 18 },
      hovertext: "Generation is below the load this month. Click for alternative marine technologies.",
      captureevents: true,
    }));
    const note = document.getElementById("deficit-note");
    note.hidden = !deficit.length;
    document.getElementById("deficit-text").textContent = deficit.length
      ? `Generation is below the load in ${window.BlueGrid.deficitMonths.join(", ")}.` : "";

    plot("chart-monthly", traces, {
      barmode: "stack",
      margin: { l: 50, r: 20, t: deficit.length ? 40 : 20, b: 40 },
      yaxis: { title: "MWh" },
      xaxis: { title: "Month", dtick: 1 },
      annotations,
    }, { responsive: true, displaylogo: false }).then((gd) => {
      gd.removeAllListeners?.("plotly_clickannotation");
      gd.on("plotly_clickannotation", (e) => {
        // after this click has finished: the info box closes on clicks outside it
        if (e.annotation?.text === "❗") setTimeout(() => document.getElementById("btn-deficit").click(), 0);
      });
    });
  }

  // One small radar per technology (colours come from the theme, by technology name).
  const RADARS = [
    { key: "Wind", id: "chart-radar-wind" },
    { key: "Floating Solar PV", id: "chart-radar-fpv" },
    { key: "OTEC", id: "chart-radar-otec" },
    { key: "Wave", id: "chart-radar-wave" },
  ];

  function renderRadar(techScores) {
    const cats = ["Resource", "CAPEX", "Reliability", "Sustainability"];
    RADARS.forEach(({ key, id }) => {
      const s = techScores[key];
      if (!s || !document.getElementById(id)) return;
      plot(id, [{
        type: "scatterpolar",
        r: [s.resource, s.capex, s.reliability, s.sustainability, s.resource],
        theta: [...cats, cats[0]],
        fill: "toself",
        name: key,
        hovertemplate: "<b>%{theta}</b>: %{r:.1f}<extra></extra>", // exact score on hover
      }], {
        polar: {
          radialaxis: {
            range: [0, 100],
            visible: true,
            tickfont: { size: 9 },
            angle: 90,     // scale numbers along the top spoke, clear of the shape
            tickangle: 0,
            dtick: 50,     // 0 / 50 / 100 only: six labels don't fit on the short spoke
          },
          angularaxis: { direction: "clockwise", rotation: 90, tickfont: { size: 11 } },
        },
        showlegend: false,
        margin: { l: 92, r: 64, t: 30, b: 30 }, // room for "Sustainability" (left) / "CAPEX" (right)
      }, { responsive: true, displaylogo: false, displayModeBar: false });
    });
  }

  function renderRanked(list) {
    if (!list || !list.length) {
      els.ranked.innerHTML = '<p class="muted">No feasible configuration found.</p>';
      return;
    }
    const rows = list.slice(0, 10).map((r, i) => {
      const c = r.capacities;
      const inr = (x) => x.toLocaleString("en-IN", { maximumFractionDigits: 0 });
      return `<tr>
        <td>${i + 1}</td>
        <td>${c.wind_kW} / ${c.solar_kWp} / ${c.otec_kW} / ${c.wave_kW}</td>
        <td>${c.bess_kWh}</td>
        <td>₹${r.lcoe.toFixed(2)}</td>
        <td>${(r.coverage * 100).toFixed(1)}%</td>
        <td>${(r.plf * 100).toFixed(1)}%</td>
        <td>${inr(r.co2_avoided_t)} t</td>
        <td>₹${(r.capex_INR / 1e7).toFixed(1)} Cr</td>
      </tr>`;
    }).join("");
    els.ranked.innerHTML = `
      <table class="ranked-table">
        <thead><tr>
          <th>#</th>
          <th>Wind / Solar / OTEC / Wave (kW)</th>
          <th>BESS (kWh)</th>
          <th>LCOE ₹/kWh</th>
          <th>Coverage</th>
          <th>PLF</th>
          <th>CO₂ avoided</th>
          <th>CAPEX</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  async function postJSON(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  }

  async function doEvaluate() {
    els.status.textContent = "Evaluating…";
    const body = {
      island: els.island.value,
      load_kW: Number(els.load.value),
      capacities: state.capacities,
    };
    const resp = await postJSON("/api/evaluate", body);
    els.status.textContent = resp.ok ? "" : "error";
    if (!resp.ok) { alert(resp.error); return; }
    
    state.lastResult = resp.result;
    state.lastRunId = resp.run_id; // Save the ID
    
    // Enable the export buttons
    document.getElementById("btn-export-csv").disabled = false;
    document.getElementById("btn-export-pdf").disabled = false;

    // Timezone of the hourly data behind this result
    const tzBadge = document.getElementById("timezone-badge");
    if (tzBadge && resp.result.timezone) tzBadge.textContent = `(Timezone: ${resp.result.timezone})`;

    renderKPIs(resp.result);
    renderDiscount(resp.result);
    renderMonthly(resp.result);
    renderStats(resp.result);
    renderRadar(resp.result.tech_scores);
  }

  // Full-screen "Optimizing…" loading screen (busy.css); blurs and blocks the page.
  function setBusy(busy) {
    const overlay = document.getElementById("busy-overlay");
    if (overlay) overlay.hidden = !busy;
    document.querySelector("main")?.setAttribute("aria-busy", String(busy));
  }

  async function doOptimize() {
    setBusy(true);
    try {
      await runOptimize();
    } catch (err) {
      els.status.textContent = "error";
      alert(err.message || err);
    } finally {
      setBusy(false);
    }
  }

  async function runOptimize() {
    els.status.textContent = "Optimizing… (this can take up to 60s)";
    const body = {
      island: els.island.value,
      load_kW: Number(els.load.value),
      // minimum shares, % → fraction of the load
      ...Object.fromEntries(MIX_SLIDERS.map(({ key }) => [key, state.mix[key] / 100])),
    };
    const resp = await postJSON("/api/optimize", body);
    els.status.textContent = resp.ok ? "" : "error";
    if (!resp.ok) { alert(resp.error); return; }
    
    renderRanked(resp.result.feasible);
    // The PDF report lists these mixes when it's for the same place and load
    state.lastOptimize = { id: resp.opt_id, island: body.island, load_kW: body.load_kW };

    // Auto-apply the top mix
    if (resp.result.recommended) {
      const c = resp.result.recommended.capacities;
      Object.assign(state.capacities, c);
      SLIDERS.forEach(({ key }) => {
        const el = document.getElementById("sl-" + key);
        const out = document.getElementById("out-" + key);
        if (el) { 
          // Expand the slider's maximum visually if the optimizer found a higher value
          if (c[key] > el.max) {
             el.max = Math.ceil(c[key] * 1.25); // Expand max bound by 25% overhead
          }
          el.value = c[key]; 
          out.textContent = c[key]; 
        }
      });
      
      await doEvaluate(); 
    }
  }

  async function doCompare() {
    els.status.textContent = "Comparing all islands…";
    const body = {
      load_kW: Number(els.load.value),
      capacities: state.capacities,
    };
    const resp = await postJSON("/api/compare", body);
    els.status.textContent = resp.ok ? "" : "error";
    if (!resp.ok) { alert(resp.error); return; }

    // Show the panel
    document.getElementById("panel-compare").style.display = "block";
    
    const data = resp.result;
    const islands = data.map(d => d.island);
    const lcoe = data.map(d => d.lcoe);
    const cos = data.map(d => d.cos);
    
    // 1. Render Grouped Bar Chart
    plot("chart-compare", [
      { x: islands, y: lcoe, name: "LCOE (RE) ₹/kWh", type: "bar", marker: { color: "#0b3d91" } },
      { x: islands, y: cos, name: "System CoS ₹/kWh", type: "bar", marker: { color: "#a5b4fc" } }
    ], {
      barmode: "group",
      margin: { l: 50, r: 20, t: 30, b: 60 },
      xaxis: { tickangle: -45 },
      yaxis: { title: "INR / kWh" },
      legend: { orientation: "h", y: 1.1 }
    }, { responsive: true, displaylogo: false });

    // 2. Render Table
    const rows = data.map(r => `
      <tr>
        <td><strong>${r.island}</strong></td>
        <td>₹${r.lcoe.toFixed(2)}</td>
        <td>₹${r.cos.toFixed(2)}</td>
        <td>${(r.lpsp * 100).toFixed(1)}%</td>
        <td>${(r.plf * 100).toFixed(1)}%</td>
        <td>₹${(r.capex_INR / 1e7).toFixed(1)} Cr</td>
      </tr>
    `).join("");

    document.getElementById("table-compare").innerHTML = `
      <table class="ranked-table">
        <thead><tr>
          <th>Island</th>
          <th>LCOE (RE)</th>
          <th>System CoS</th>
          <th>LPSP</th>
          <th>PLF</th>
          <th>CAPEX</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
    
    // Scroll to the comparison panel
    document.getElementById("panel-compare").scrollIntoView({ behavior: 'smooth' });
  }

  function resetAll() {
    state.capacities = { wind_kW: 1500, solar_kWp: 1500, otec_kW: 500, wave_kW: 0, bess_kWh: 4000 };
    buildSliders();
    state.mix = defaultMix();
    buildMixSliders();
  }

  document.addEventListener("DOMContentLoaded", () => {
    buildSliders();
    buildMixSliders();
    document.getElementById("btn-evaluate").addEventListener("click", doEvaluate);
    document.getElementById("btn-optimize").addEventListener("click", doOptimize);
    document.getElementById("btn-compare").addEventListener("click", doCompare);
    document.getElementById("btn-reset").addEventListener("click", resetAll);
    
    // Add Export Listeners
    document.getElementById("btn-export-csv").addEventListener("click", () => {
      if (state.lastRunId) window.location.href = `/export/csv/${state.lastRunId}`;
    });
    document.getElementById("btn-export-pdf").addEventListener("click", () => {
      if (!state.lastRunId) return;
      const r = state.lastResult, o = state.lastOptimize;
      const sameRun = o && r && o.island === r.island && o.load_kW === r.capacities.load_kW;
      window.location.href = `/export/pdf/${state.lastRunId}` + (sameRun ? `?opt=${o.id}` : "");
    });
  });
})();