/* Plotly theme for the planner's dark glass panels.
   Exposes window.BlueGrid.plot(id, traces, layout, config): Plotly.newPlot with
   transparent backgrounds, light text, faint grids, and one fixed colour per series. */
(() => {
  const INK = "#eef2f7", MUTED = "#b4c0cd", GRID = "rgba(255,255,255,0.10)";
  // One colour per series (validated for colour-blind separation and contrast on the dark glass).
  const SERIES_COLORS = {
    "Wind": "#3987e5", "FPV": "#d95926", "Floating Solar PV": "#d95926",
    "OTEC": "#199e70", "Wave": "#c98500",
    "LCOE (RE) ₹/kWh": "#3987e5", "System CoS ₹/kWh": "#d95926",
  };

  const isObj = (v) => v && typeof v === "object" && !Array.isArray(v);
  const merge = (base, extra) => {
    const out = { ...base };
    for (const [k, v] of Object.entries(extra)) out[k] = isObj(v) && isObj(base[k]) ? merge(base[k], v) : v;
    return out;
  };
  const rgba = (hex, a) => {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  };

  const axis = { gridcolor: GRID, linecolor: GRID, zerolinecolor: GRID, tickfont: { color: MUTED } };
  // Axis titles may be given as plain strings; keep their text while recolouring.
  const themeAxis = (a = {}, extra = {}) => {
    const text = typeof a.title === "string" ? a.title : a.title?.text;
    return merge(a, { ...axis, ...extra, title: { text, font: { color: MUTED } } });
  };

  function themeTrace(t) {
    if (t.name === "Load") return merge(t, { line: { color: INK, width: 2, dash: "dash" } });
    const color = SERIES_COLORS[t.name];
    if (!color) return t;
    if (t.type === "bar") return merge(t, { marker: { color, line: { color: "rgba(12,22,36,0.9)", width: 2 } } });
    if (t.type === "scatterpolar") return merge(t, { line: { color, width: 2 }, fillcolor: rgba(color, 0.15), marker: { color, size: 7 } });
    return t;
  }

  function themeLayout(layout) {
    const themed = merge(layout, {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: "Inter, system-ui, sans-serif", color: MUTED, size: 12 },
      legend: { font: { color: INK }, traceorder: "normal", bgcolor: "rgba(0,0,0,0)" },
      hoverlabel: { bgcolor: "#12202f", bordercolor: "rgba(255,255,255,0.25)", font: { color: INK } },
      modebar: { bgcolor: "rgba(0,0,0,0)", color: MUTED, activecolor: INK },
    });
    if (layout.polar) {
      themed.polar = merge(layout.polar, {
        bgcolor: "rgba(0,0,0,0)",
        radialaxis: { gridcolor: GRID, linecolor: GRID, tickfont: { color: MUTED } },
        angularaxis: { gridcolor: GRID, linecolor: GRID, tickfont: { color: INK } },
      });
    } else {
      themed.xaxis = themeAxis(layout.xaxis, { automargin: true }); // room for long island names
      themed.yaxis = themeAxis(layout.yaxis);
    }
    return themed;
  }

  window.BlueGrid = window.BlueGrid || {};
  window.BlueGrid.plot = (id, traces, layout, config) =>
    Plotly.newPlot(id, traces.map(themeTrace), themeLayout(layout), config);
})();
