# BlueGrid — Core Mathematical & Economic Formulation

## 1. Symbol Table

| Symbol | Meaning | Unit |
|---|---|---|
| $m$ | month index 1..12 | — |
| $h_m$ | hours in month $m$ | h |
| $P_w, P_s, P_o, P_v$ | installed capacity of wind / solar / OTEC / wave | kW |
| $E_b$ | BESS nameplate energy | kWh |
| $P_b^{\max}$ | BESS max discharge power | kW |
| $\mathrm{CF}^{\text{wind}}_m$ | net monthly wind capacity factor | — |
| $\mathrm{CF}^{\text{fpv}}_m$ | net monthly floating-PV CF | — |
| $\mathrm{CF}^{\text{otec}}_m$ | net monthly OTEC CF | — |
| $\mathrm{CF}^{\text{wave}}_m$ | net monthly wave CF | — |
| $L$ | target net AC load | kW |
| $\Delta t$ | dispatch interval | 1 h |

---

## 2. Mathematical Formulation

### 2.1 Monthly Generation per Technology

**Wind**
$$
E^{\text{wind}}_m = P_w \cdot \mathrm{CF}^{\text{wind}}_m \cdot h_m \quad [\text{kWh}]
$$

**Floating solar PV**
$$
E^{\text{fpv}}_m = P_s \cdot \mathrm{CF}^{\text{fpv}}_m \cdot h_m \quad [\text{kWh}]
$$
*(Alternatively: $E^{\text{fpv}}_m = P_s \cdot \frac{\mathrm{PVOUT}_m}{1000}$ in MWh)*

**OTEC**
$$
\mathrm{NOF}(\Delta T) = \mathrm{clip}\!\left(\frac{(\Delta T / 22)^2 - 0.30}{1 - 0.30},\ 0,\ 1.05\right)
$$
$$
\mathrm{CF}^{\text{otec}}_m = \mathrm{NOF}(\Delta T_m) \times 0.92 \quad (\text{availability})
$$
$$
E^{\text{otec}}_m = P_o \cdot \mathrm{CF}^{\text{otec}}_m \cdot h_m \quad [\text{kWh}]
$$

**Wave**
$$
E^{\text{wave}}_m = P_v \cdot \mathrm{CF}^{\text{wave}}_m \cdot h_m \quad [\text{kWh}]
$$

### 2.2 Energy Balance (Monthly)

$$
\mathrm{Gen}_m = E^{\text{wind}}_m + E^{\text{fpv}}_m + E^{\text{otec}}_m + E^{\text{wave}}_m
$$
$$
\mathrm{Load}_m = L \cdot h_m \quad [\text{kWh}]
$$
$$
\mathrm{Delivered}_m = \min(\mathrm{Gen}_m, \mathrm{Load}_m)
$$
$$
\mathrm{Surplus}_m = \max(0,\ \mathrm{Gen}_m - \mathrm{Load}_m)
$$
$$
\mathrm{Unmet}_m = \max(0,\ \mathrm{Load}_m - \mathrm{Gen}_m)
$$
$$
\mathrm{Coverage}_m = \frac{\mathrm{Delivered}_m}{\mathrm{Load}_m}
$$

### 2.3 Hourly Dispatch (BESS & Reliability)

For each hour $t = 1 \dots 8760$ with dispatch step $\Delta t = 1\,\text{h}$:

**Generation & Net Load**
$$
G_t = P_w \cdot \mathrm{cf}^{\text{wind}}_t + P_s \cdot \mathrm{cf}^{\text{fpv}}_t + P_o \cdot \mathrm{cf}^{\text{otec}}_t + P_v \cdot \mathrm{cf}^{\text{wave}}_t
$$
$$
N_t = G_t - L_t
$$

**BESS Parameters**
- $E_b$ — nameplate energy (kWh)
- $\mathrm{DoD}$ — depth of discharge (0.9)
- $\eta_c = \eta_d = \sqrt{0.88} \approx 0.9381$ (Round Trip Efficiency = 88%)
- $P_b^{\max} = 0.5 \cdot E_b$
- $S_{\max} = E_b \cdot \mathrm{DoD}$
- $S_{\min} = E_b \cdot (1-\mathrm{DoD})$

**Chronological Update ($S_t$ = State of Charge)**
$$
\Delta_c = \min\!\left( \max(N_t,0),\ \frac{S_{\max} - S_{t-1}}{\eta_c},\ P_b^{\max} \right)
$$
$$
\Delta_d = \min\!\left( \max(-N_t,0),\ (S_{t-1} - S_{\min}) \cdot \eta_d,\ P_b^{\max},\ \max(0, L_t - G_t) \right)
$$
$$
S_t = S_{t-1} + \eta_c \Delta_c - \frac{\Delta_d}{\eta_d}
$$

**Hourly Metrics**
$$
\mathrm{Del}_t = \min(G_t + \Delta_d,\ L_t)
$$
$$
\mathrm{Unmet}_t = \max(0,\ L_t - G_t - \Delta_d)
$$
$$
\mathrm{Curt}_t = \max(0,\ N_t - \Delta_c)
$$

### 2.4 Reliability and Performance Metrics

**Loss of Power Supply Probability (LPSP)**
$$
\mathrm{LPSP} = \frac{\sum_t \mathrm{Unmet}_t}{\sum_t L_t}
$$

**Worst Month Coverage (if using monthly data)**
$$
\mathrm{WorstMonthCoverage} = \min_{m} \mathrm{Coverage}_m
$$

**Plant Load Factor (PLF)**
$$
\mathrm{PLF}_{\text{target}} = \frac{\sum_t \mathrm{Del}_t}{L \cdot 8760}
$$
$$
\mathrm{PLF}_{\text{fleet}} = \frac{\sum_t G_t}{(P_w + P_s + P_o + P_v) \cdot 8760}
$$

---

## 3. Economics Engine

### 3.1 Capital Recovery Factor (CRF)

$$
\mathrm{CRF} = \frac{r (1+r)^n}{(1+r)^n - 1}
$$
*(where $r$ = real discount rate, $n$ = project life in years)*

### 3.2 CAPEX & Subsidies

$$
C_i = P_i \cdot \mathrm{CAPEX}^{\text{tech}}_{\text{island}} \quad \text{for } i \in \{w, s, o, v\}
$$
$$
C_b = E_b \cdot \mathrm{CAPEX}^{\text{bess}}_{\text{island}}
$$
$$
\mathrm{Sub} = \mathrm{flag} \cdot \left( P_s \cdot \mathrm{CFA}_{\text{fpv}} + E_b \cdot \mathrm{VGF}_{\text{bess}} \right)
$$
$$
C^{\text{net}} = \sum C_i + C_b - \mathrm{Sub}
$$

### 3.3 OPEX (Annual)

$$
\mathrm{OM}_i = P_i \cdot \mathrm{OPEX}^{\text{island}}_i
$$
$$
\mathrm{OM}_b = C_b \cdot \frac{\mathrm{OPEX\%}_{\text{bess}}}{\text{1 yr}}
$$
$$
\mathrm{OM}^{\text{yr}} = \sum_i \mathrm{OM}_i + \mathrm{OM}_b
$$

### 3.4 BESS Replacement (Present Value)

$$
\mathrm{PV}_b^{\text{repl}} = \frac{C_b \cdot f_{\text{repl}}}{(1+r)^{y_{\text{repl}}}}
$$
*(where $f_{\text{repl}} = 0.6$, $y_{\text{repl}} = 15$)*

### 3.5 Diesel Cost of Unmet Energy

$$
F^{\text{diesel}} = \mathrm{Unmet}_{\text{MWh}} \cdot 1000 \cdot \mathrm{SFC} \cdot P^{\text{diesel}}_{\text{INR/L}}
$$
*(where SFC = 0.3 L/kWh)*

### 3.6 Levelized Costs

**LCOE of RE-only delivered energy** (INR/kWh):
$$
\mathrm{LCOE}_{\text{RE}} = \frac{(C^{\text{net}} + \mathrm{PV}_b^{\text{repl}}) \cdot \mathrm{CRF} + \mathrm{OM}^{\text{yr}}}{\mathrm{Delivered}_{\text{kWh}}}
$$

**System cost per kWh of load served** (includes diesel top-up):
$$
\mathrm{CoS} = \frac{(C^{\text{net}} + \mathrm{PV}_b^{\text{repl}}) \cdot \mathrm{CRF} + \mathrm{OM}^{\text{yr}} + F^{\text{diesel}}}{\mathrm{Load}_{\text{kWh}}}
$$

---

## 4. Carbon Engine

### 4.1 Emission Factors

$$
\mathrm{EF}_{\text{diesel}} = \mathrm{SFC}\, [\mathrm{L/kWh}] \times \mathrm{EF}^{\text{comb}}_L\, [\mathrm{kg/L}] / 1000 \ \ [\mathrm{t/MWh}]
$$
*(Value: 0.3 × 2.68 = 0.804 tCO₂/MWh)*

### 4.2 Avoided Emissions & Credits

$$
\mathrm{CO2}^{\text{avoided}} = \mathrm{Delivered}_{\text{MWh}} \cdot \mathrm{EF}_{\text{diesel}} \quad [\text{tCO₂/yr}]
$$
$$
\mathrm{Credit} = \mathrm{CO2}^{\text{avoided}} \cdot P_{\text{carbon,INR/t}}
$$

---

## 5. Scoring Matrix & Optimization

### 5.1 Optimization Problem

$$
\min_{P_w, P_s, P_o, P_v, E_b}\ \mathrm{LCOE}
$$
$$
\text{s.t.}\quad \mathrm{LPSP}(P_w, P_s, P_o, P_v, E_b) \le 0.01
$$
$$
\quad\quad P_i \le P_i^{\max} \quad \text{(land / lagoon constraints)}
$$

### 5.2 Scoring Criteria per Configuration

**Resource Potential** (0–10):
$$
R_{\text{cfg}} = 10 \cdot \frac{\sum_i P_i \overline{\mathrm{CF}}_i}{\sum_i P_i} \ \Big/ \max_{\text{cfg}} (\cdot)
$$

**CAPEX** (0–10):
$$
K_{\text{cfg}} = 10 \cdot \frac{\min_{\text{cfg}} \mathrm{LCOE}}{\mathrm{LCOE}_{\text{cfg}}}
$$

**Reliability** (0–10):
$$
R\!e_{\text{cfg}} = 10 \cdot (1 - \mathrm{LPSP}_{\text{cfg}})
$$

**Sustainability** (0–10):
$$
\mathrm{CO2}^{\text{lifecycle}}_{\text{cfg}} = \sum_i \frac{E_i \cdot \mathrm{gCO2}_i}{1000} \quad [\text{kgCO₂}] \text{ p.a.}
$$
$$
S_{\text{cfg}} = 10 \cdot \left(1 - \frac{\mathrm{CO2}^{\text{lifecycle}}_{\text{cfg}}}{\max_{\text{cfg}} \mathrm{CO2}^{\text{lifecycle}}}\right)
$$

**Weighted Score:**
$$
\mathrm{Score}_{\text{cfg}} = w_R R_{\text{cfg}} + w_K K_{\text{cfg}} + w_{Re} R\!e_{\text{cfg}} + w_S S_{\text{cfg}}
$$

---

## 6. Core Units & Assumptions Register

### 6.1 Units Conversions
*   **Power:** kW (Net AC at point of delivery)
*   **Energy:** kWh or MWh (Multiply kWh by $10^{-3}$ for MWh)
*   **Irradiance:** kWh/m²/day (GHI)
*   **Temperature / ΔT:** °C (Surface − 1000 m)
*   **Currency:** INR (All maths in INR. Lakh = $10^5$, Crore = $10^7$)

### 6.2 Key Default Assumptions
*   **Discount rate ($r$):** 8% real
*   **Project life ($n$):** 25 years
*   **BESS Replacement:** At year 15 at 60% of original CAPEX ($f_{\text{repl}} = 0.6$).
*   **Diesel Constants:** Landed price ≈ ₹100/L; Specific Fuel Consumption = 0.3 L/kWh.
*   **CF Adjustments:** All input CFs are strictly *net* (inclusive of availability, wake, electrical, soiling, temperature, and inverter losses).