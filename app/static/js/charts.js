/* BlueGrid UI: sliders, fetch calls, charts. */
(() => {
  const SLIDERS = [
    { key: "wind_kW",   label: "Wind" },
    { key: "solar_kWp", label: "Floating solar" },
    { key: "otec_kW",   label: "OTEC" },
    { key: "wave_kW",   label: "Wave" },
    { key: "bess_kWh",  label: "BESS" },
  ];

  const state = {
    capacities: { wind_kW: 1500, solar_kWp: 1500, otec_kW: 500, wave_kW: 0, bess_kWh: 4000 },
    lastResult: null,
    lastRunId: null,
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
    const html = SLIDERS.map(({ key, label }) => {
      const [lo, hi] = bounds[key];
      const s = step[key];
      const v = state.capacities[key];
      return `
        <label style="margin-bottom:10px;">
          <span>${label} — <output id="out-${key}">${v}</output></span>
          <input type="range" id="sl-${key}" min="${lo}" max="${hi}" step="${s}" value="${v}">
        </label>`;
    }).join("");
    els.sliders.innerHTML = html;
    SLIDERS.forEach(({ key }) => {
      const el = document.getElementById("sl-" + key);
      const out = document.getElementById("out-" + key);
      el.addEventListener("input", () => {
        state.capacities[key] = Number(el.value);
        out.textContent = el.value;
      });
    });
  }

  function kpiCard(label, value, sub) {
    return `<div class="kpi"><div class="kpi-label">${label}</div>
            <div class="kpi-value">${value}</div>
            <div class="kpi-sub">${sub || ""}</div></div>`;
  }

  function renderKPIs(r) {
    const e = r.econ, c = r.carbon, rel = r.reliability, a = r.annual;
    const lpsp = rel.lpsp_hourly ?? rel.lpsp_monthly;
    const inr = (x) => x.toLocaleString("en-IN", { maximumFractionDigits: 0 });
    const num = (x, d = 2) => Number(x).toFixed(d);
    els.kpis.innerHTML = [
      kpiCard("LCOE (RE only)", `₹${num(e.LCOE_RE_INR_per_kWh)}`, "per kWh delivered"),
      kpiCard("System cost", `₹${num(e.cost_of_service_INR_per_kWh)}`, "incl. diesel top-up"),
      kpiCard("PLF vs target", `${num(r.plf_target * 100, 1)}%`, `${inr(a.delivered_kWh / 1000)} MWh served`),
      kpiCard("LPSP", `${num(lpsp * 100)}%`, rel.lpsp_hourly != null ? "hourly" : "monthly"),
      kpiCard("CO₂ avoided", `${inr(c.co2_avoided_t)} t`, "per year"),
      kpiCard("Carbon credit", `₹${inr(c.carbon_credit_INR)}`, "per year"),
      kpiCard("CAPEX", `₹${num(e.capex_INR / 1e7, 1)} Cr`, "island-adjusted"),
      kpiCard("Unmet", `${inr(a.unmet_kWh / 1000)} MWh`, "diesel top-up"),
    ].join("");
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
    Plotly.newPlot("chart-monthly", traces, {
      barmode: "stack",
      margin: { l: 50, r: 20, t: 20, b: 40 },
      yaxis: { title: "MWh" },
      xaxis: { title: "Month", dtick: 1 },
    }, { responsive: true, displaylogo: false });
  }

  function renderRadar(techScores) {
    const cats = ["Resource", "CAPEX", "Reliability", "Sustainability"];
    const techs = Object.keys(techScores);
    const traces = techs.map((t) => {
      const s = techScores[t];
      return {
        type: "scatterpolar",
        r: [s.resource, s.capex, s.reliability, s.sustainability, s.resource],
        theta: [...cats, cats[0]],
        fill: "toself",
        name: t,
      };
    });
    Plotly.newPlot("chart-radar", traces, {
      polar: { radialaxis: { range: [0, 10], visible: true } },
      showlegend: true, margin: { l: 40, r: 40, t: 20, b: 20 },
    }, { responsive: true, displaylogo: false });
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

    renderKPIs(resp.result);
    renderMonthly(resp.result);
    renderRadar(resp.result.tech_scores);
  }

  async function doOptimize() {
    els.status.textContent = "Optimizing… (this can take up to 60s)"; // Updated expected time
    const body = {
      island: els.island.value,
      load_kW: Number(els.load.value),
    };
    const resp = await postJSON("/api/optimize", body);
    els.status.textContent = resp.ok ? "" : "error";
    if (!resp.ok) { alert(resp.error); return; }
    
    renderRanked(resp.result.feasible);
    
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

  function resetAll() {
    state.capacities = { wind_kW: 1500, solar_kWp: 1500, otec_kW: 500, wave_kW: 0, bess_kWh: 4000 };
    buildSliders();
  }

  document.addEventListener("DOMContentLoaded", () => {
    buildSliders();
    document.getElementById("btn-evaluate").addEventListener("click", doEvaluate);
    document.getElementById("btn-optimize").addEventListener("click", doOptimize);
    document.getElementById("btn-reset").addEventListener("click", resetAll);
    
    // Add Export Listeners
    document.getElementById("btn-export-csv").addEventListener("click", () => {
      if (state.lastRunId) window.location.href = `/export/csv/${state.lastRunId}`;
    });
    document.getElementById("btn-export-pdf").addEventListener("click", () => {
      if (state.lastRunId) window.location.href = `/export/pdf/${state.lastRunId}`;
    });
  });
})();