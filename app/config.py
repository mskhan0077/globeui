"""UI defaults, slider bounds, scoring weights."""

APP_DEFAULTS = {
    "load_kW": 1000,
    "bounds": {
        "wind_kW":   (0, 3000),
        "solar_kWp": (0, 3000),
        "otec_kW":   (0, 1500),
        "wave_kW":   (0, 1000),
        "bess_kWh":  (0, 10000),
    },
    "step": {
        "wind_kW":   100,
        "solar_kWp": 100,
        "otec_kW":   100,
        "wave_kW":   100,
        "bess_kWh":  500,
    },
    "reliability_target_lpsp": 0.01,
    "weights": {
        "resource": 0.30, "capex": 0.25,
        "reliability": 0.25, "sustainability": 0.20,
    },
}