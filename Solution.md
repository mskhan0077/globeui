# BlueGrid — Optimization Formulation (WIP)

## 1. Core Problem
We have an island with a flat load and renewable generation choices:
- Wind
- Floating PV (FPV)
- OTEC
- Wave (optional)
- BESS (battery)

We want to find capacity sizes:
$$
P_w, P_s, P_o, P_v \ge 0 \quad [\text{kW}]
$$
$$
E_b \ge 0 \quad [\text{kWh}]
$$

Objective:
$$
\min \quad \text{Total Annualized Cost}(P_w, P_s, P_o, P_v, E_b)
$$
subject to:
$$
\text{Unmet Load Fraction} \le \varepsilon
$$