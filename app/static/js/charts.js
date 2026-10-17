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
    return `<div class="kpi">
              <div class="kpi-label">${label}</div>
              <div class="kpi-value">${value}</div>
              <div class="kpi-sub">${sub || ""}</div>
            </div>`;
  }

  function renderKPIs(r) {
    const e = r.econ, c = r.carbon, rel = r.reliability, a = r.annual;
    const lpsp = rel.lpsp_hourly ?? rel.lpsp_annual ?? rel.lpsp_monthly;
    const inr = (x) => x.toLocaleString("en-IN", { maximumFractionDigits: 0 });
    const num = (x, d = 2) => Number(x).toFixed(d);
    
    const nomRate = e.nominal_discount_rate ? (e.nominal_discount_rate * 100).toFixed(2) : "N/A";

    els.kpis.innerHTML = [
      kpiCard("LCOE (RE only)", `₹${num(e.LCOE_RE_INR_per_kWh)}`, "per kWh delivered"),
      kpiCard("System cost", `₹${num(e.cost_of_service_INR_per_kWh)}`, "incl. diesel top-up"),
      kpiCard("Nominal Rate", `${nomRate}%`, "WACC + Inflation"),
      kpiCard("PLF vs target", `${num(r.plf_target * 100, 1)}%`, `${inr(a.delivered_kWh / 1000)} MWh served`),
      kpiCard("LPSP", `${num(lpsp * 100)}%`, rel.lpsp_hourly != null ? "hourly" : "annual"),
      kpiCard("CO₂ avoided", `${inr(c.co2_avoided_t)} t`, "per year"),
      kpiCard("CAPEX", `₹${num(e.capex_INR / 1e7, 1)} Cr`, "island-adjusted"),
      kpiCard("Unmet", `${inr(a.unmet_kWh / 1000)} MWh`, "diesel top-up"),
    ].join("");
  }

  function renderStats(r) {
    const container = document.getElementById("stats-container");
    const grid = document.getElementById("stats-grid");
    
    if (!r.stats || Object.keys(r.stats).length === 0) {
      container.style.display = "none";
      return;
    }
    
    container.style.display = "block";
    
    const labels = {
      "wind": "Wind", "solar": "Floating Solar", 
      "otec": "OTEC", "wave": "Wave", "load": "System Load"
    };

    let html = "";
    for (const [key, s] of Object.entries(r.stats)) {
      // Skip techs with zero generation to keep it clean
      if (key !== "load" && s.max === 0) continue; 

      html += `
        <div class="stat-card">
          <div class="stat-title">${labels[key] || key}</div>
          <div class="stat-row"><span>Mean</span> <span>${s.mean.toFixed(1)}</span></div>
          <div class="stat-row"><span>Median</span> <span>${s.median.toFixed(1)}</span></div>
          <div class="stat-row"><span>Std Dev</span> <span>${s.std.toFixed(1)}</span></div>
          <div class="stat-row"><span>Min</span> <span>${s.min.toFixed(1)}</span></div>
          <div class="stat-row"><span>Max</span> <span>${s.max.toFixed(1)}</span></div>
        </div>
      `;
    }
    
    grid.innerHTML = html;
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
    const configs = [
        { key: "Wind", id: "chart-radar-wind", color: "#1f77b4" },
        { key: "Floating Solar PV", id: "chart-radar-fpv", color: "#ff7f0e" },
        { key: "OTEC", id: "chart-radar-otec", color: "#2ca02c" },
        { key: "Wave", id: "chart-radar-wave", color: "#d62728" },
    ];

    configs.forEach(({ key, id, color }) => {
        const s = techScores[key];
        const chartDiv = document.getElementById(id);
        
        if (s && chartDiv) {
            const trace = {
                type: "scatterpolar",
                r: [s.resource, s.capex, s.reliability, s.sustainability, s.resource],
                theta: [...cats, cats[0]],
                fill: "toself",
                name: key,
                line: { color: color },
                hovertemplate: "<b>%{theta}</b>: %{r:.1f}<extra></extra>"
            };
            
            Plotly.newPlot(id, [trace], {
                polar: {
                    radialaxis: { range: [0, 100], visible: true, tickfont: { size: 9 }, angle: 90, tickangle: 0 },
                    angularaxis: { direction: "clockwise", rotation: 90, tickfont: { size: 11 } },
                },
                showlegend: false,
                margin: { l: 60, r: 60, t: 30, b: 30 }, 
            }, { responsive: true, displaylogo: false });
        }
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
    state.lastRunId = resp.run_id;
    
    document.getElementById("btn-export-csv").disabled = false;
    document.getElementById("btn-export-pdf").disabled = false;

    const tzBadge = document.getElementById("timezone-badge");
    if (tzBadge && resp.result.timezone) {
        tzBadge.textContent = "(Timezone: " + resp.result.timezone + ")";
    }

    renderKPIs(resp.result);
    renderStats(resp.result);
    renderMonthly(resp.result);
    renderRadar(resp.result.tech_scores);
  }

  async function doOptimize() {
    els.status.textContent = "Optimizing… (this can take up to 60s)";
    const body = {
      island: els.island.value,
      load_kW: Number(els.load.value),
    };
    const resp = await postJSON("/api/optimize", body);
    els.status.textContent = resp.ok ? "" : "error";
    if (!resp.ok) { alert(resp.error); return; }
    
    renderRanked(resp.result.feasible);
    
    if (resp.result.recommended) {
      const c = resp.result.recommended.capacities;
      Object.assign(state.capacities, c);
      SLIDERS.forEach(({ key }) => {
        const el = document.getElementById("sl-" + key);
        const out = document.getElementById("out-" + key);
        if (el) { 
          if (c[key] > el.max) { el.max = Math.ceil(c[key] * 1.25); }
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

    document.getElementById("panel-compare").style.display = "block";
    
    const data = resp.result;
    const islands = data.map(d => d.island);
    const lcoe = data.map(d => d.lcoe);
    const cos = data.map(d => d.cos);
    
    Plotly.newPlot("chart-compare", [
      { x: islands, y: lcoe, name: "LCOE (RE) ₹/kWh", type: "bar", marker: { color: "#0b3d91" } },
      { x: islands, y: cos, name: "System CoS ₹/kWh", type: "bar", marker: { color: "#a5b4fc" } }
    ], {
      barmode: "group",
      margin: { l: 50, r: 20, t: 30, b: 60 },
      yaxis: { title: "INR / kWh" },
      legend: { orientation: "h", y: 1.1 }
    }, { responsive: true, displaylogo: false });

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
    
    document.getElementById("btn-export-csv").addEventListener("click", () => {
      if (state.lastRunId) window.location.href = `/export/csv/${state.lastRunId}`;
    });
    document.getElementById("btn-export-pdf").addEventListener("click", () => {
      if (state.lastRunId) window.location.href = `/export/pdf/${state.lastRunId}`;
    });

    // Modal Logic
    const modal = document.getElementById("dcf-modal");
    const btnOpen = document.getElementById("btn-open-dcf");
    const btnClose = document.querySelector(".close-btn");

    if (btnOpen && modal && btnClose) {
      btnOpen.addEventListener("click", () => {
        modal.classList.add("show");
      });
      
      btnClose.addEventListener("click", () => {
        modal.classList.remove("show");
      });
      
      window.addEventListener("click", (e) => {
        if (e.target === modal) {
          modal.classList.remove("show");
        }
      });
    }
  });
})();