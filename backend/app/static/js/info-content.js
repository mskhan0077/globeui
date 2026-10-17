/* Text for the planner's (i) boxes on charts and KPIs (shown by info.js).
   Each entry: { title, html(ctx), needsFinance?, refs? }. refs are keys of the reference
   list (backend/app/references.py), shown as numbered citations like [3, 7].
   ctx = { finance: finance_params.json values, defaults: planner defaults, fmt: { inr, pct } }.
   Formulas mirror backend/app/engine (economics.py, carbon.py, scoring.py, config_eval.py). */
(() => {
  const p = (...lines) => lines.map((l) => `<p>${l}</p>`).join("");
  const formula = (f) => `<p class="info-box__formula">${f}</p>`;
  const num = (x, d = 2) => Number(x).toFixed(d);

  // Cost benchmarks behind the island CAPEX figures
  const COST_REFS = ["kerc-wind-2026", "ctuil-benchmarks-2026", "giz-floating-pv-2024",
    "irena-otec-2014", "oes-lcoe-2015", "ember-bess-2025"];

  // Inflation inputs of the nominal DCF model, with the engine's defaults
  // (economics.py) for any that finance_params.json doesn't list.
  const dcf = (f) => {
    const general = f.inflation_rate_general ?? 0.05;
    return {
      general,
      opex: f.inflation_rate_opex ?? 0.04,
      diesel: f.inflation_rate_diesel ?? 0.07,
      bess: f.inflation_rate_bess ?? -0.05,
      nominal: (1 + Number(f.discount_rate_real)) * (1 + general) - 1,
    };
  };

  window.BlueGrid = window.BlueGrid || {};

  // References for each technology's (i) box (costs, life-cycle emissions)
  window.BlueGrid.techRefs = {
    "Wind": ["kerc-wind-2026", "ctuil-benchmarks-2026", "ipcc-ar5-annex3"],
    "Floating Solar PV": ["giz-floating-pv-2024", "pm-ssy-2026", "ipcc-ar5-annex3"],
    "OTEC": ["irena-otec-2014", "oes-lcoe-2015"],
    "Wave": ["oes-lcoe-2015", "wave-india-2025"],
    "BESS": ["ctuil-benchmarks-2026", "ember-bess-2025", "bess-vgf-2025"],
  };

  window.BlueGrid.infoContent = {
    // ---------- charts ----------
    monthly: {
      title: "Monthly energy balance",
      html: () =>
        p("How much electricity each technology generates in each month (MWh) for the capacities on the sliders, stacked by technology.",
          "The dashed line is the demand: target load × hours in the month. Where the bars rise above it there is surplus (stored in the battery or curtailed); below it, the battery and then diesel must cover the gap.",
          "When the place has hourly data, each month is the total of an hour-by-hour (8,760-hour) simulation; otherwise it uses monthly average capacity factors."),
      refs: ["open-meteo-2023", "era5-2020"],
    },
    viability: {
      title: "Technology viability scores (0–100)",
      html: () =>
        p("One chart per technology, scoring how well it suits this place on four criteria. Each is 0–100 and relative to the other technologies (higher is better). They don’t depend on the slider capacities.") +
        `<dl class="info-box__defs">
          <dt>Resource</dt><dd>100 × its average capacity factor ÷ the best technology’s</dd>
          <dt>CAPEX</dt><dd>100 × cheapest island CAPEX per kW ÷ its CAPEX</dd>
          <dt>Reliability</dt><dd>100 × (10th-percentile month’s capacity factor ÷ its average) × TRL ÷ 9: steadiness and maturity</dd>
          <dt>Sustainability</dt><dd>100 × (1 − its lifecycle gCO₂/kWh ÷ the highest)</dd>
        </dl>`,
      refs: ["global-wind-atlas-2023", "global-solar-atlas-2019", "era5-2020", "ipcc-ar5-annex3", "irena-otec-2014"],
    },

    ranked: {
      title: "Ranked configurations",
      html: ({ defaults: d, fmt }) =>
        p("The best capacity mixes found by Find optimal mix for this place and load, best first. The top one is applied to the sliders and evaluated.") +
        `<dl class="info-box__defs">
          <dt>1. Search</dt>
          <dd>An exact linear program (cheapest mix on monthly totals, with battery self-discharge and the inflating diesel price), plus a coarse grid of mixes: wind and floating solar up to 10× the load, OTEC up to 2×, wave up to 4×, battery up to 50 hours of load. Grid mixes that couldn’t generate enough energy in a year even with no losses are skipped.</dd>
          <dt>2. Check</dt>
          <dd>Every mix, including the linear program’s, is simulated hour by hour (8,760 h) with the battery. Only mixes with LPSP ≤ ${fmt.pct(d.reliability_target_lpsp ?? 0.05, 0)} are kept.</dd>
          <dt>3. Rank</dt>
          <dd>score = 1 ÷ LCOE + 0.1 × (1 ÷ CAPEX in ₹ Cr): the cheapest electricity wins, lower CAPEX breaks near-ties. Wasted (curtailed) energy isn’t penalised.</dd>
        </dl>` +
        p("Columns: capacities (kW, battery in kWh), then LCOE, coverage (1 − LPSP), PLF, CO₂ avoided and CAPEX for that mix; see the KPI (i)s for how each is calculated. The top 10 are shown."),
    },
    compare: {
      title: "Multi-island comparison",
      html: () =>
        p("The capacity mix currently on the sliders, evaluated on every place BlueGrid has data for, with the same target load, sorted by LCOE (cheapest first).",
          "The bars compare LCOE (renewables only) with the system cost, which also pays for diesel top-up.",
          "For speed this uses monthly totals rather than the hour-by-hour simulation, so LPSP is optimistic (it can’t see night-time gaps) and may differ from the KPIs above. Use it to see where a mix works best, then evaluate that place for exact figures."),
    },

    // ---------- KPIs ----------
    lcoe: {
      title: "LCOE (renewables only)",
      needsFinance: true,
      html: ({ finance: f, fmt }) => {
        const d = dcf(f);
        return p("Levelised cost of the renewable electricity actually delivered, per kWh. Excludes diesel.") +
          formula("[(CAPEX − subsidies + battery replacement) × CRF + present value of O&amp;M × CRF] ÷ energy delivered per year") +
          p(`A nominal discounted cash flow over ${num(f.project_life_yr, 0)} years (see 💡 Nominal DCF model): O&amp;M rises ${fmt.pct(d.opex, 0)} a year, and the battery replacement in year ${num(f.bess_replacement_year, 0)} is priced with battery costs changing ${fmt.pct(d.bess, 0)} a year.`,
            `CRF (capital recovery factor) at the ${fmt.pct(d.nominal, 1)} nominal rate turns present values into an equal yearly cost.`);
      },
      refs: COST_REFS,
    },
    cos: {
      title: "System cost (cost of service)",
      needsFinance: true,
      html: ({ finance: f, fmt }) => {
        const d = dcf(f);
        return p("Average cost per kWh of meeting the whole demand, including the diesel needed for whatever the renewables and battery don’t cover.") +
          formula("(present value of capital + O&amp;M + diesel fuel) × CRF ÷ total demand per year") +
          p(`Diesel fuel costs ${fmt.inr(f.diesel_fuel_cost_INR_per_kWh)} per unmet kWh in year 1 and rises ${fmt.pct(d.diesel, 0)} a year, so diesel-reliant mixes cost more over the project life.`);
      },
      refs: ["lok-sabha-pac-2022"],
    },
    nominal: {
      title: "Nominal discount rate",
      needsFinance: true,
      html: ({ finance: f, fmt }) => {
        const d = dcf(f);
        return p("The rate future costs are discounted at. It combines the real cost of capital with general inflation, because the future costs themselves include inflation.") +
          formula("r_nom = (1 + r_real) × (1 + inflation) − 1") +
          p(`Here (1 + ${fmt.pct(Number(f.discount_rate_real), 0)}) × (1 + ${fmt.pct(d.general, 0)}) − 1 = ${fmt.pct(d.nominal, 2)}.`);
      },
    },
    dcf: {
      title: "Nominal discounted cash flow (DCF)",
      needsFinance: true,
      html: ({ finance: f, fmt }) => {
        const d = dcf(f);
        return p(`LCOE and System cost add up every cost over the ${num(f.project_life_yr, 0)}-year project life in nominal terms (with inflation), discount them to today, then spread them into an equal yearly cost.`) +
          `<dl class="info-box__defs">
            <dt>Diesel fuel</dt><dd>rises ${fmt.pct(d.diesel, 0)} a year (historical CAGR in India)</dd>
            <dt>O&amp;M</dt><dd>rises ${fmt.pct(d.opex, 0)} a year</dd>
            <dt>Battery replacement</dt><dd>${d.bess < 0 ? "falls" : "rises"} ${fmt.pct(Math.abs(d.bess), 0)} a year (battery prices keep dropping)</dd>
          </dl>` +
          formula(`r_nom = (1 + r_real) × (1 + inflation) − 1 = ${fmt.pct(d.nominal, 2)}`) +
          p("Discounting inflating costs at a nominal rate counts future costs correctly, so mixes that lean on diesel for years are penalised as they should be.");
      },
    },
    plf: {
      title: "PLF vs target",
      html: () =>
        p("Plant load factor against the target: the share of the target demand that renewables (with the battery) actually supply over the year. 100% means the full load is met every hour.") +
        formula("energy delivered ÷ (target load × 8,760 h)") +
        p("The figure below it is the energy delivered per year."),
    },
    lpsp: {
      title: "LPSP (loss of power supply probability)",
      needsFinance: true,
      html: ({ finance: f, defaults: d, fmt }) =>
        p("Share of the year’s demand that goes unmet.") +
        formula("unmet energy ÷ total demand") +
        p(`<strong>hourly</strong>: from an hour-by-hour simulation with battery dispatch (round-trip efficiency ${fmt.pct(f.bess_round_trip_eff, 0)}, usable up to ${fmt.pct(f.bess_depth_of_discharge, 0)} of capacity, max C-rate ${num(f.bess_max_c_rate, 1)}, 1.5% self-discharge per hour). <strong>annual</strong>: from monthly totals only (no hourly data for the place), which is optimistic because it can’t see night-time gaps.`,
          d.reliability_target_lpsp != null ? `Find optimal mix only accepts mixes with LPSP ≤ ${fmt.pct(d.reliability_target_lpsp, 0)}.` : ""),
    },
    co2: {
      title: "CO₂ avoided",
      needsFinance: true,
      html: ({ finance: f }) =>
        p("Diesel CO₂ emissions avoided each year because renewables supply the energy instead. Only delivered energy counts, not curtailed surplus.") +
        formula(`energy delivered (MWh) × ${num(f.diesel_emission_factor_tCO2_per_MWh, 3)} tCO₂/MWh`) +
        p("The factor is the diesel generators’ emission intensity."),
      refs: ["ipcc-2006-combustion", "lok-sabha-pac-2022"],
    },
    capex: {
      title: "CAPEX",
      needsFinance: true,
      html: ({ finance: f, fmt }) =>
        p("Upfront investment for the capacities on the sliders, using island-adjusted unit costs (marine logistics, cyclone-rated foundations, etc.).") +
        formula("Σ capacity × island CAPEX per kW (per kWh for the battery) − subsidies") +
        p(Number(f.apply_subsidies_flag) > 0.5
            ? `Subsidies are on: ${fmt.inr(f.fpv_cfa_subsidy_INR_per_kW)}/kW for floating solar and ${fmt.inr(f.bess_vgf_INR_per_kWh)}/kWh for the battery.`
            : "Subsidies are currently off.",
          "Each technology’s unit cost is in its (i) next to the sliders. Shown in crore (1 Cr = ₹1,00,00,000)."),
      refs: [...COST_REFS, "pm-ssy-2026", "bess-vgf-2025"],
    },
    unmet: {
      title: "Unmet energy",
      needsFinance: true,
      html: ({ finance: f, fmt }) =>
        p("Electricity demand that renewables and the battery can’t supply over the year. It’s assumed to be covered by diesel generators.") +
        formula("total demand − energy delivered") +
        p(`Costed in System cost at ${fmt.inr(f.diesel_fuel_cost_INR_per_kWh)} per kWh in year 1, rising ${fmt.pct(dcf(f).diesel, 0)} a year.`),
      refs: ["lok-sabha-pac-2022"],
    },
  };
})();
