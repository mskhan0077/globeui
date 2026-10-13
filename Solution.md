# BlueGrid — Optimization Formulation (WIP)

## 1. Problem Statement
Find sizing vectors $P = [P_w, P_s, P_o, P_v]^\top \ge 0$ and storage $E_b \ge 0$ minimizing annual cost.

## 2. Indices
- $t \in \mathcal{T} = \{1, \dots, 8760\}$.
- $i \in \mathcal{G} = \{w, s, o, v\}$.

## 3. Physical Constraints

### 3.1 Generation Limit
$$
g_i[t] - \mathrm{CF}_i[t] P_i \le 0 \quad \forall i \in \mathcal{G}, \forall t \in \mathcal{T}
$$

### 3.2 Bus Power Balance
Renewables + storage discharge + unmet must equal load + storage charge + curtailed energy:
$$
\sum_{i \in \mathcal{G}} g_i[t] + \mathrm{dis}[t] - \mathrm{ch}[t] - k[t] + u[t] = L[t] \quad \forall t \in \mathcal{T}
$$
Where:
- $k[t] \ge 0$: curtailed renewable generation (kW).
- $u[t] \ge 0$: unmet load (kW).
- $\mathrm{dis}[t], \mathrm{ch}[t] \ge 0$: battery power flows (kW).