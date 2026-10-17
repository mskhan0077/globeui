"""Chronological BESS dispatch and reliability metrics."""
from __future__ import annotations

import numpy as np

def dispatch_hourly(
    gen_kW: np.ndarray,
    load_kW: np.ndarray,
    bess_kWh: float,
    rte: float = 0.88,
    dod: float = 0.9,
    c_rate: float = 0.5,
) -> dict:
    """Dispatch BESS over hourly generation and load profiles."""
    eta = float(np.sqrt(rte))
    pmax = c_rate * bess_kWh
    
    # ALIGNED WITH LP: Max SOC is DoD * Capacity. Min SOC is 0.
    smax = dod * bess_kWh
    smin = 0.0 
    n = len(gen_kW)
    
    self_discharge_rate = 0.015 

    soc = 0.5 * smax
    delivered = np.zeros(n)
    unmet = np.zeros(n)
    curtailed = np.zeros(n)
    soc_hist = np.zeros(n)

    for t in range(n):
        # Apply strict multi-day discharge penalty
        if soc > smin:
            soc = max(smin, soc * (1.0 - self_discharge_rate))
            
        net = gen_kW[t] - load_kW[t]
        if net >= 0:
            room = max(smax - soc, 0.0)
            charge = min(net, room / eta, pmax)
            soc += eta * charge
            curtailed[t] = max(net - charge, 0.0)
            delivered[t] = min(gen_kW[t], load_kW[t])
        else:
            need = -net
            avail = max(soc - smin, 0.0) * eta
            discharge = min(need, avail, pmax)
            soc -= discharge / eta
            delivered[t] = min(gen_kW[t] + discharge, load_kW[t])
            unmet[t] = max(load_kW[t] - gen_kW[t] - discharge, 0.0)
        soc_hist[t] = soc

    total_load = float(load_kW.sum())
    total_unmet = float(unmet.sum())
    return {
        "delivered_kWh": float(delivered.sum()),
        "unmet_kWh": total_unmet,
        "curtailed_kWh": float(curtailed.sum()),
        "lpsp": total_unmet / max(total_load, 1e-9),
        "lole_hours": int((unmet > 1e-9).sum()),
        "soc_kWh": soc_hist.tolist(),
        "hourly_delivered": delivered,
        "hourly_unmet": unmet,
        "hourly_curtailed": curtailed,
    }