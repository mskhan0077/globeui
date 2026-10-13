# BlueGrid — Optimization Formulation (WIP)

## 1. Indices & Sets
- $t \in \mathcal{T} = \{1, \dots, T\}$, $T = 8760$.
- $i \in \mathcal{G} = \{w, s, o, v\}$.

## 2. Decision Variables
- Capacity: $P_i \ge 0$ (kW), $E_b \ge 0$ (kWh).
- Dispatch: $g_i[t] \ge 0$, $\mathrm{ch}[t] \ge 0$, $\mathrm{dis}[t] \ge 0$, $u[t] \ge 0$, $k[t] \ge 0$, and state of charge $\mathrm{soc}[t] \ge 0$.

## 3. Physical Constraints

### 3.1 Resource & Bus Balance
$$
g_i[t] \le \mathrm{CF}_i[t] P_i \quad \forall i, t
$$
$$
\sum_{i \in \mathcal{G}} g_i[t] + \mathrm{dis}[t] - \mathrm{ch}[t] - k[t] + u[t] = L[t] \quad \forall t
$$

### 3.2 Battery State of Charge (SOC) Dynamics
With time-step $\Delta t = 1$ h and one-way efficiencies $\eta_c, \eta_d$:
$$
\mathrm{soc}[t] = \mathrm{soc}[t-1] + \eta_c \cdot \mathrm{ch}[t] - \frac{\mathrm{dis}[t]}{\eta_d} \quad \forall t \in \{1, \dots, T\}
$$
Assuming symmetric round-trip efficiency:
$$
\eta_c = \eta_d = \sqrt{\mathrm{RTE}}
$$