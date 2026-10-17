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
    smax = dod * bess_kWh
    smin = 0.0
    n = len(gen_kW)
    
    self_discharge_rate = 0.015 

    soc = 0.5 * smax
    delivered = np.zeros(n)
    unmet = np.zeros(n)
    curtailed = np.zeros(n)
    soc_hist = np.zeros(n)

    # Local variable assignment for speed
    _sd = 1.0 - self_discharge_rate
    _eta = eta
    _pmax = pmax
    _smax = smax
    _gen = gen_kW
    _load = load_kW

    for t in range(n):
        if soc > smin:
            soc = max(smin, soc * _sd)
            
        net = _gen[t] - _load[t]
        if net >= 0:
            room = _smax - soc
            if room < 0.0:
                room = 0.0
            charge = net
            room_eta = room / _eta
            if room_eta < charge:
                charge = room_eta
            if _pmax < charge:
                charge = _pmax
                
            soc += _eta * charge
            spill = net - charge
            curtailed[t] = spill if spill > 0.0 else 0.0
            delivered[t] = _gen[t] if _gen[t] < _load[t] else _load[t]
        else:
            need = -net
            avail = (soc - smin) * _eta
            if avail < 0.0:
                avail = 0.0
            discharge = need
            if avail < discharge:
                discharge = avail
            if _pmax < discharge:
                discharge = _pmax
                
            soc -= discharge / _eta
            served = _gen[t] + discharge
            delivered[t] = served if served < _load[t] else _load[t]
            short = _load[t] - served
            unmet[t] = short if short > 0.0 else 0.0
            
        soc_hist[t] = soc

    total_load = float(np.sum(_load))
    total_unmet = float(np.sum(unmet))
    
    return {
        "delivered_kWh": float(np.sum(delivered)),
        "unmet_kWh": total_unmet,
        "curtailed_kWh": float(np.sum(curtailed)),
        "lpsp": total_unmet / max(total_load, 1e-9),
        "lole_hours": int(np.sum(unmet > 1e-9)),
        "soc_kWh": soc_hist.tolist(),
        "hourly_delivered": delivered,
        "hourly_unmet": unmet,
        "hourly_curtailed": curtailed,
    }