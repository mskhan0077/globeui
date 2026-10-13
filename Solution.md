# BlueGrid — Optimal Sizing as a Linear Program: Complete Mathematical Formulation

## 1. Problem Formulation
The goal is to determine the optimal installed capacities of renewable generation $P_i$ ($i \in \{w, s, o, v\}$) and battery energy storage capacity $E_b$ to minimize annualized expenditure while meeting net load within a specified loss of power supply probability (LPSP) bound $\varepsilon$.

$$
\min_{P_i, E_b} \quad \text{Annualized System Cost}
$$
$$
\text{s.t.} \quad \text{Hourly Bus Balance}, \quad \text{Storage Dynamics}, \quad \text{LPSP} \le \varepsilon, \quad P_i, E_b \ge 0
$$

---

## 2. Notation & Parameters

### 2.1 Sets & Indices
- $t \in \mathcal{T} = \{1, \dots, T\}$: Hourly dispatch step, where $T = 8760$, $\Delta t = 1$ h.
- $i \in \mathcal{G} = \{w, s, o, v\}$: Generation sources (Wind, Solar FPV, OTEC, Wave).

### 2.2 Parameters
- $\mathrm{CF}_i[t]$: Net hourly capacity factor for technology $i$ (dimensionless, $[0, 1]$).
- $L[t]$: Net electrical demand at hour $t$ (kW).
- $\mathrm{capex}_i$: Island-adjusted capital cost per kW (INR/kW).
- $\mathrm{capex}_b$: Island-adjusted battery capital cost per kWh (INR/kWh).
- $\mathrm{opex}_i$: Annual operating cost per kW (INR/kW/yr).
- $\beta_b$: Battery annual operating cost ratio ($\text{OPEX} / \text{CAPEX}$).
- $r$: Real discount rate / WACC (fraction).
- $n_i, n_{\text{proj}}$: Technology and overall project lifetimes (years).
- $f_{\text{repl}}, y_{\text{repl}}$: BESS mid-life replacement cost fraction and replacement year.
- $\eta_c, \eta_d$: Battery one-way charge and discharge efficiencies ($\eta_c = \eta_d = \sqrt{\mathrm{RTE}}$).
- $\mathrm{DoD}$: Usable depth of discharge fraction ($[0, 1]$).
- $\rho_b$: Storage maximum power-to-energy ratio (C-rate, $\text{h}^{-1}$).
- $\mathrm{CFA}_s, \mathrm{VGF}_b$: Capital subsidies for solar and storage (INR/kW, INR/kWh).
- $c_{\text{diesel}}$: Landed marginal diesel fuel generation cost (INR/kWh).
- $\varepsilon$: Maximum allowable annual LPSP threshold.
- $P_i^{\max}$: Spatial capacity upper bound (kW).

### 2.3 Decision Variables
- $P_i \ge 0$: Installed capacity of generator $i$ (kW).
- $E_b \ge 0$: Nameplate energy capacity of battery storage (kWh).
- $g_i[t] \ge 0$: Active power dispatched from generator $i$ at hour $t$ (kW).
- $\mathrm{ch}[t], \mathrm{dis}[t] \ge 0$: Battery charge and discharge power at hour $t$ (kW).
- $\mathrm{soc}[t] \ge 0$: Battery stored energy at hour $t$ (kWh).
- $u[t] \ge 0$: Unmet energy deficit / diesel generation requirement at hour $t$ (kW).
- $k[t] \ge 0$: Curtailed renewable generation at hour $t$ (kW).

---

## 3. Economic Formulation

### 3.1 Capital Recovery Factor (CRF)
Converting an upfront capital investment $C$ into an equivalent annualized series over $n$ years at discount rate $r$:
$$
C = \sum_{k=1}^n \frac{A}{(1+r)^k} = A \left[ \frac{1 - (1+r)^{-n}}{r} \right] \implies \mathrm{CRF}(r, n) = \frac{r(1+r)^n}{(1+r)^n - 1}
$$

### 3.2 Consolidated Cost Objective Coefficients
The total annualized cost is linear in the decision variables:
$$
\min \quad \sum_{i \in \mathcal{G}} a_i P_i + a_b E_b + c_{\text{diesel}} \sum_{t \in \mathcal{T}} u[t]
$$
where:
$$
a_i = \mathrm{capex}_i \cdot \mathrm{CRF}(r, n_i) + \mathrm{opex}_i - \delta_{i,s} \left[ \mathrm{CFA}_s \cdot \mathrm{CRF}(r, n_{\text{proj}}) \right]
$$
$$
a_b = \mathrm{capex}_b \left[ \mathrm{CRF}(r, n_b) + \beta_b + \frac{f_{\text{repl}}}{(1+r)^{y_{\text{repl}}}} \mathrm{CRF}(r, n_{\text{proj}}) \right] - \mathrm{VGF}_b \cdot \mathrm{CRF}(r, n_{\text{proj}})
$$

---

## 4. Canonical Linear Program

$$
\boxed{
\begin{aligned}
\min_{P, E_b, g, \mathrm{ch}, \mathrm{dis}, \mathrm{soc}, u, k} \quad & \sum_{i \in \mathcal{G}} a_i P_i + a_b E_b + c_{\text{diesel}} \sum_{t=1}^T u[t] \\[6pt]
\text{s.t.} \quad & g_i[t] - \mathrm{CF}_i[t] P_i \le 0 && \forall i \in \mathcal{G}, \forall t \in \mathcal{T} \\
& \sum_{i \in \mathcal{G}} g_i[t] + \mathrm{dis}[t] - \mathrm{ch}[t] - k[t] + u[t] = L[t] && \forall t \in \mathcal{T} \\
& \mathrm{soc}[t] - \mathrm{soc}[t-1] - \eta_c \mathrm{ch}[t] + \frac{\mathrm{dis}[t]}{\eta_d} = 0 && \forall t \in \mathcal{T} \\
& \mathrm{soc}[T] - \mathrm{soc}[0] = 0 && \\
& \mathrm{soc}[t] - \mathrm{DoD} \cdot E_b \le 0 && \forall t \in \mathcal{T} \\
& \mathrm{ch}[t] - \rho_b E_b \le 0 && \forall t \in \mathcal{T} \\
& \mathrm{dis}[t] - \rho_b E_b \le 0 && \forall t \in \mathcal{T} \\
& u[t] - L[t] \le 0 && \forall t \in \mathcal{T} \\
& \sum_{t=1}^T u[t] - \varepsilon \sum_{t=1}^T L[t] \le 0 && \\
& P_i \le P_i^{\max} && \forall i \in \mathcal{G} \\
& P_i, E_b, g_i[t], \mathrm{ch}[t], \mathrm{dis}[t], \mathrm{soc}[t], u[t], k[t] \ge 0 && \forall i, \forall t
\end{aligned}
}
$$

---