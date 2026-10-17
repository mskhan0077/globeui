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

  // Chart rendering (dark glass theme) lives in theme.js.
  const plot = window.BlueGrid.plot;

  const state = {
    capacities: { wind_kW: 1500, solar_kWp: 1500, otec_kW: 500, wave_kW: 0, bess_kWh: 4000 },
    lastResult: null,
    lastRunId: null,
    lastOptimize: null, // { id, island, load_kW } of the last Find optimal mix
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
    els.kpis.innerHTML = [
      kpiCard("LCOE (RE only)", `₹${num(e.LCOE_RE_INR_per_kWh)}`, "per kWh delivered", "lcoe"),
      kpiCard("System cost", `₹${num(e.cost_of_service_INR_per_kWh)}`, "incl. diesel top-up", "cos"),
      kpiCard("Nominal rate", e.nominal_discount_rate != null ? `${num(e.nominal_discount_rate * 100)}%` : "N/A", "WACC + inflation", "nominal"),
      kpiCard("PLF vs target", `${num(r.plf_target * 100, 1)}%`, `${inr(a.delivered_kWh / 1000)} MWh served`, "plf"),
      kpiCard("LPSP", `${num(lpsp * 100)}%`, rel.lpsp_hourly != null ? "hourly" : "annual", "lpsp"),
      kpiCard("CO₂ avoided", `${inr(c.co2_avoided_t)} t`, "per year", "co2"),
      kpiCard("CAPEX", `₹${num(e.capex_INR / 1e7, 1)} Cr`, "island-adjusted", "capex"),
      kpiCard("Unmet", `${inr(a.unmet_kWh / 1000)} MWh`, "diesel top-up", "unmet"),
    ].join("");
    window.BlueGrid.info?.close(); // its button may just have been replaced
    window.BlueGrid.info?.attach(els.kpis);
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
    plot("chart-monthly", traces, {
      barmode: "stack",
      margin: { l: 50, r: 20, t: 20, b: 40 },
      yaxis: { title: "MWh" },
      xaxis: { title: "Month", dtick: 1 },
    }, { responsive: true, displaylogo: false });
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
    renderMonthly(resp.result);
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
  }

  document.addEventListener("DOMContentLoaded", () => {
    buildSliders();
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