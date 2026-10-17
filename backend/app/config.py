"""UI defaults, slider bounds."""
APP_DEFAULTS = {
    "load_kW": 1000,
    "bounds": {
        "wind_kW":   (0, 5000),
        "solar_kWp": (0, 5000),
        "otec_kW":   (0, 3000),
        "wave_kW":   (0, 5000),
        "bess_kWh":  (0, 50000),
    },
    "step": {
        "wind_kW":   100,
        "solar_kWp": 100,
        "otec_kW":   100,
        "wave_kW":   100,
        "bess_kWh":  500,
    },
    # Find optimal mix must meet the whole load (team main since 2026-10-17, c8b7205)
    "reliability_target_lpsp": 0.0,
    # Optimizer diversity constraints: minimum capacity per technology, as a share of the
    # target load (0.2 = at least 20% of the load in kW). 0 = no minimum.
    "min_wind_pct": 0.0,
    "min_solar_pct": 0.0,
    "min_otec_pct": 0.0,
    "min_wave_pct": 0.0,
}
