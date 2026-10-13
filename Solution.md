# BlueGrid — Optimization Formulation (WIP)

## 1. Problem Statement
Find sizing vectors $P = [P_w, P_s, P_o, P_v]^\top \ge 0$ and storage $E_b \ge 0$ minimizing annual cost such that load is served reliably.

## 2. Indices
- $t \in \{1, \dots, 8760\}$: hourly dispatch interval ($\Delta t = 1$ h).
- $i \in \{w, s, o, v\}$: generation technologies.

## 3. Resource Availability
Dispatched power $g_i[t]$ at any hour cannot exceed installed nameplate capacity scaled by net capacity factor $\mathrm{CF}_i[t]$:

$$
g_i[t] \le \mathrm{CF}_i[t] \cdot P_i \quad \forall i, \forall t
$$