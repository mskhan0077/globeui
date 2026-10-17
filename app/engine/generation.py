"""Monthly generation + BESS reservoir.

This module computes the monthly energy balance for one configuration.
BESS is modelled as a monthly reservoir (energy shifted between months,
not intra-day). For hourly dispatch, see bess.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

def monthly_generation(island: str, capacities: dict, dfs: dict) -> pd.DataFrame:
    """Return a DataFrame indexed by month with generation / load / BESS flows."""
    w = dfs["wind"].loc[island]
    s = dfs["solar"].loc[island]
    o = dfs["otec"].loc[island]
    v = dfs["wave"].loc[island]

    months = sorted(w.index.get_level_values("month_num").unique())

    def col(df, name):
        return df[name].reindex(months).astype(float).values

    hours = col(w, "hours")
    cf_w = col(w, "cf_net_after_losses")
    cf_s = col(s, "cf_fpv")
    cf_o = col(o, "cf_otec")
    cf_v = col(v, "cf_wec_net")

    P_w = float(capacities["wind_kW"])
    P_s = float(capacities["solar_kWp"])
    P_o = float(capacities["otec_kW"])
    P_v = float(capacities["wave_kW"])
    E_b = float(capacities["bess_kWh"])
    L = float(capacities["load_kW"])

    gen_w = P_w * cf_w * hours
    gen_s = P_s * cf_s * hours
    gen_o = P_o * cf_o * hours
    gen_v = P_v * cf_v * hours
    gen_total = gen_w + gen_s + gen_o + gen_v
    load = L * hours
    net = gen_total - load

    if E_b > 0:
        dod = float(dfs["finance"]["bess_depth_of_discharge"])
        eta = float(np.sqrt(dfs["finance"]["bess_round_trip_eff"]))
        soc_max = E_b * dod
        soc = 0.5 * soc_max

        delivered = np.zeros(len(months))
        unmet = np.zeros(len(months))
        surplus = np.zeros(len(months))
        curtailed = np.zeros(len(months))

        for i, n in enumerate(net):
            if n >= 0:
                charge = min(n, (soc_max - soc) / eta)
                soc += eta * charge
                curtailed[i] = max(n - charge, 0.0)
                delivered[i] = load[i]
                unmet[i] = 0.0
                surplus[i] = n
            else:
                need = -n
                discharge = min(need, soc * eta)
                soc -= discharge / eta
                delivered[i] = min(gen_total[i] + discharge, load[i])
                unmet[i] = max(need - discharge, 0.0)
    else:
        delivered = np.minimum(gen_total, load)
        unmet = np.maximum(load - gen_total, 0.0)
        surplus = np.maximum(gen_total - load, 0.0)
        curtailed = np.zeros_like(surplus)

    df = pd.DataFrame(
        {
            "hours": hours,
            "cf_wind": cf_w,
            "cf_fpv": cf_s,
            "cf_otec": cf_o,
            "cf_wave": cf_v,
            "gen_wind_kWh": gen_w,
            "gen_fpv_kWh": gen_s,
            "gen_otec_kWh": gen_o,
            "gen_wave_kWh": gen_v,
            "gen_total_kWh": gen_total,
            "load_kWh": load,
            "delivered_kWh": delivered,
            "surplus_kWh": surplus,
            "curtailed_kWh": curtailed,
            "unmet_kWh": unmet,
            "coverage": np.where(load > 0, delivered / load, 0.0),
        },
        index=months,
    )
    df.index.name = "month_num"
    return df