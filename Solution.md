# BlueGrid — Optimal Sizing as a Linear Program: Mathematical Formulation

## 1. Problem Definition
The objective is to choose installed capacities $P_w, P_s, P_o, P_v$ and BESS energy $E_b$ that minimize the annualized cost of serving a target load at or above a specified reliability threshold.

$$
\min_{\{P_i, E_b\}} \; \text{Annualized Cost}
$$
$$
\text{subject to } \text{hourly physics, storage dynamics, LPSP} \le \varepsilon, \text{ and } P_i, E_b \ge 0.
$$

---

## 2. Notation and Parameters

### 2.1 Indices and Sets

| Symbol | Meaning |
|---|---|
| $t \in \mathcal{T}$ | hour of the year, $\|\mathcal{T}\| = T = 8760$ |
| $m \in \mathcal{M}$ | month, $\|\mathcal{M}\| = 12$ |
| $i \in \mathcal{G}$ | generation tech: $w$ (wind), $s$ (solar), $o$ (OTEC), $v$ (wave) |
| $b$ | BESS |

### 2.2 Parameters

| Symbol | Meaning | Unit |
|---|---|---|
| $\mathrm{CF}_i[t]$ | capacity factor of tech $i$ at hour $t$ (net of losses) | – |
| $L[t]$ | net AC load at hour $t$ | kW |
| $\mathrm{capex}_i$ | island-adjusted CAPEX per kW (or per kWh for BESS) | INR |
| $\mathrm{opex}_i$ | island-adjusted annual OPEX per kW | INR/yr |
| $\beta_b$ | BESS OPEX as fraction of CAPEX | – |
| $n_i$ | plant lifetime | yr |
| $r$ | real discount rate (WACC) | – |
| $f_{\text{repl}}$ | BESS replacement cost fraction | – |
| $y_{\text{repl}}$ | BESS replacement year | yr |
| $\eta_c, \eta_d$ | one-way charge / discharge efficiencies | – |
| $\mathrm{DoD}$ | depth of discharge | – |
| $\rho_b$ | c-rate (max power / energy) | 1/h |
| $\mathrm{CFA}_s$ | floating-PV subsidy | INR/kW |
| $\mathrm{VGF}_b$ | BESS VGF subsidy | INR/kWh |
| $c_{\text{diesel}}$ | diesel fuel cost | INR/kWh of unmet |
| $\varepsilon$ | LPSP target (e.g., 0.01) | – |
| $P_i^{\max}$ | maximum installed capacity constraint | kW |

### 2.3 Decision Variables

**Design Variables (Continuous, Non-negative):**
$$
P_w,\ P_s,\ P_o,\ P_v \ge 0 \quad [\text{kW}]
$$
$$
E_b \ge 0 \quad [\text{kWh}]
$$

**Dispatch Variables (Per hour $t$, Continuous, Non-negative):**
$$
g_i[t] \ge 0 \quad [\text{kW}] \quad \text{for } i \in \{w,s,o,v\}
$$
$$
\mathrm{ch}[t],\ \mathrm{dis}[t] \ge 0 \quad [\text{kW}]
$$
$$
\mathrm{soc}[t] \ge 0 \quad [\text{kWh}]
$$
$$
u[t] \ge 0 \quad [\text{kW}] \quad \text{(unmet load, served by diesel)}
$$
$$
k[t] \ge 0 \quad [\text{kW}] \quad \text{(curtailed RE)}
$$

---

## 3. Physical Model

### 3.1 Generation Limits
Dispatched generation cannot exceed available resource at hour $t$. This constraint is linear as $\mathrm{CF}_i[t]$ is a fixed coefficient:
$$
g_i[t] - \mathrm{CF}_i[t] \, P_i \le 0 \qquad \forall i \in \mathcal{G},\ \forall t \in \mathcal{T}. \tag{G}
$$

### 3.2 Hourly Energy Balance
At every hour, total generation plus battery discharge minus battery charge minus curtailment plus unmet load must equal the target load:
$$
\sum_{i \in \mathcal{G}} g_i[t] + \mathrm{dis}[t] - \mathrm{ch}[t] - k[t] + u[t] = L[t] \qquad \forall t \in \mathcal{T}. \tag{B}
$$

### 3.3 BESS State-of-Charge (SOC) Dynamics
$$
\mathrm{soc}[t] = \mathrm{soc}[t-1] + \eta_c \, \mathrm{ch}[t] \, \Delta t - \frac{\mathrm{dis}[t]}{\eta_d} \, \Delta t \qquad \forall t \in \mathcal{T}. \tag{S}
$$
Where $\eta_c = \eta_d = \sqrt{\mathrm{RTE}}$ assuming symmetric efficiency losses.

**Cyclic Boundary Condition:** To ensure energy balance over the year, the final state of charge must equal the initial state:
$$
\mathrm{soc}[T] - \mathrm{soc}[0] = 0. \tag{S-cyc}
$$

### 3.4 BESS Power and Energy Limits
$$
\mathrm{soc}[t] - \mathrm{DoD} \cdot E_b \le 0 \qquad \forall t \tag{S-cap}
$$
$$
\mathrm{ch}[t] - \rho_b \, E_b \le 0 \qquad \forall t \tag{CH}
$$
$$
\mathrm{dis}[t] - \rho_b \, E_b \le 0 \qquad \forall t \tag{DIS}
$$

### 3.5 Load and Curtailment Limits
$$
u[t] - L[t] \le 0 \qquad \forall t \tag{U}
$$
$$
k[t] \ge 0 \qquad \forall t. \tag{K}
$$

---

## 4. Reliability Constraints

**Annual Loss of Power Supply Probability (LPSP):**
$$
\sum_{t \in \mathcal{T}} u[t] \, \Delta t \;\le\; \varepsilon \sum_{t \in \mathcal{T}} L[t] \, \Delta t. \tag{LPSP}
$$

**Monthly LPSP (Optional constraint):**
$$
\sum_{t \in m} u[t] \le \varepsilon \sum_{t \in m} L[t] \qquad \forall m \in \mathcal{M}. \tag{LPSP-m}
$$

**Worst-Month Coverage (Optional constraint):**
$$
\sum_{t \in m} (L[t] - u[t]) \ge \theta \sum_{t \in m} L[t] \qquad \forall m \in \mathcal{M}. \tag{WMC}
$$

---

## 5. Economic Model

### 5.1 Capital Recovery Factor (CRF) Derivation
The annuity $A$ that has present value $C$ over $n$ years at rate $r$ solves:
$$
C = A \sum_{k=1}^{n} \frac{1}{(1+r)^k} = A \cdot \frac{1 - (1+r)^{-n}}{r}
$$
Solving for $A$ yields the Capital Recovery Factor:
$$
\mathrm{CRF}(r, n) = \frac{r (1+r)^n}{(1+r)^n - 1}. \tag{CRF}
$$

### 5.2 Annualized Costs
**Generation and Storage CAPEX:**
$$
C_i^{\text{ann}} = \mathrm{capex}_i \, \mathrm{CRF}_i \, P_i \quad [\text{INR/yr}]
$$
$$
C_b^{\text{ann}} = \mathrm{capex}_b \, \mathrm{CRF}_b \, E_b \quad [\text{INR/yr}]
$$

**Annual OPEX:**
$$
O_i = \mathrm{opex}_i \, P_i
$$
$$
O_b = \beta_b \, \mathrm{capex}_b \, E_b
$$

**BESS Replacement (Annualized):**
$$
C_b^{\text{repl,ann}} = \left( \frac{\mathrm{capex}_b \cdot E_b \cdot f_{\text{repl}}}{(1+r)^{y_{\text{repl}}}} \right) \cdot \mathrm{CRF}(r, n_{\text{proj}})
$$

**Subsidies (Annualized Deduction):**
$$
\mathrm{Sub}^{\text{ann}} = (\mathrm{CFA}_s \, P_s + \mathrm{VGF}_b \, E_b) \cdot \mathrm{CRF}(r, n_{\text{proj}})
$$

**Diesel Fallback Cost:**
$$
V^{\text{diesel}} = c_{\text{diesel}} \sum_{t \in \mathcal{T}} u[t] \, \Delta t
$$

### 5.3 Total Objective Function
$$
F(P, E_b, u) = \sum_{i \in \mathcal{G}} a_i P_i + a_b E_b + c_{\text{diesel}} \sum_{t \in \mathcal{T}} u[t] \, \Delta t \tag{F}
$$
Where the aggregated cost coefficients are:
$$
a_i = \mathrm{capex}_i \mathrm{CRF}_i + \mathrm{opex}_i \quad \text{(less } \mathrm{CFA}_s \mathrm{CRF}_{\text{proj}} \text{ for solar)}
$$
$$
a_b = \mathrm{capex}_b \mathrm{CRF}_b + \beta_b \mathrm{capex}_b + \mathrm{capex}_b f_{\text{repl}} (1+r)^{-y_{\text{repl}}} \mathrm{CRF}_{\text{proj}} - \mathrm{VGF}_b \mathrm{CRF}_{\text{proj}}
$$

---

## 6. The Full Linear Program (Canonical Form)

$$
\boxed{
\begin{aligned}
\min_{P,\, E_b,\, g,\, \mathrm{ch},\, \mathrm{dis},\, \mathrm{soc},\, u,\, k} \quad & \sum_i a_i P_i + a_b E_b + c_{\text{diesel}} \sum_t u[t] \\[4pt]
\text{s.t.} \quad & g_i[t] - \mathrm{CF}_i[t] P_i \le 0 && \forall i, t \\
& \sum_i g_i[t] + \mathrm{dis}[t] - \mathrm{ch}[t] - k[t] + u[t] = L[t] && \forall t \\
& \mathrm{soc}[t] - \mathrm{soc}[t-1] - \eta_c \mathrm{ch}[t] + \mathrm{dis}[t]/\eta_d = 0 && \forall t \\
& \mathrm{soc}[T] - \mathrm{soc}[0] = 0 && \\
& \mathrm{soc}[t] - \mathrm{DoD} \cdot E_b \le 0 && \forall t \\
& \mathrm{ch}[t] - \rho_b E_b \le 0 && \forall t \\
& \mathrm{dis}[t] - \rho_b E_b \le 0 && \forall t \\
& u[t] - L[t] \le 0 && \forall t \\
& \sum_t u[t] - \varepsilon \sum_t L[t] \le 0 && \text{(annual LPSP)} \\
& P_i \le P_i^{\max} && \forall i \\
& P_i, E_b, g_i[t], \mathrm{ch}[t], \mathrm{dis}[t], \mathrm{soc}[t], u[t], k[t] \ge 0. &&
\end{aligned}
}
$$

---

## 7. MILP Extensions (Optional Constraints)

If discrete unit counts or minimum plant sizes are required, the LP becomes a Mixed-Integer Linear Program (MILP).

**Integer Unit Sizes:**
Introduce an integer count $n_i \in \mathbb{Z}_{\ge 0}$ and a fixed unit block size $u_i$:
$$
P_i = u_i \, n_i \tag{INT}
$$

**Minimum Plant Size:**
Introduce a binary variable $z_i \in \{0, 1\}$ representing whether technology $i$ is built:
$$
P_i^{\min} \, z_i \le P_i \le P_i^{\max} \, z_i \tag{MIN}
$$

---

## 8. Multi-Objective Formulations

To generate a Pareto front or ranked decision matrix balancing Cost, LPSP, and Emissions.

**(A) $\varepsilon$-Constraint Method:**
Solve the LP iteratively by parametrically varying the target bound:
$$
\varepsilon \in \{0.20, 0.15, 0.10, 0.05, 0.02, 0.01, 0.005, 0.001\}
$$

**(B) Weighted-Sum Method:**
Combine the objectives into a single normalized scalar function:
$$
\min \quad w_1 \frac{F}{F_0} + w_2 \frac{\sum u[t]}{\sum L[t]} + w_3 \frac{\mathrm{CO_2}}{C_0}
$$
Varying the weights $w_1, w_2, w_3 \in [0, 1]$ trace the efficient frontier.