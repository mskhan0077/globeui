# BlueGrid — Optimization Formulation (WIP)

## 1. Problem Statement
Find sizing vectors $P = [P_w, P_s, P_o, P_v]^\top \ge 0$ and storage $E_b \ge 0$ minimizing annual cost.

## 2. Indices
- $t \in \mathcal{T} = \{1, \dots, 8760\}$, with $\Delta t = 1$ h.
- $i \in \mathcal{G} = \{w, s, o, v\}$.

## 3. Physical Constraints

### 3.1 Generation Limit
$$
g_i[t] - \mathrm{CF}_i[t] P_i \le 0 \quad \forall i \in \mathcal{G}, \forall t \in \mathcal{T}
$$

### 3.2 Bus Power Balance
At every hour $t$:
$$
\sum_{i \in \mathcal{G}} g_i[t] + \mathrm{dis}[t] - \mathrm{ch}[t] + u[t] = L[t]
$$
Where:
- $\mathrm{dis}[t] \ge 0$: battery discharge power (kW)
- $\mathrm{ch}[t] \ge 0$: battery charge power (kW)
- $u[t] \ge 0$: unmet demand (served by fallback diesel)
- $L[t]$: net AC load demand (kW)