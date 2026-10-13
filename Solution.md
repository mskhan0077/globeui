## 1. Problem Definition
The objective is to choose installed capacities $P_w, P_s, P_o, P_v$ and BESS energy $E_b$ that minimize the annualized cost of serving a target load at or above a specified reliability threshold.

$$
\min_{\{P_i, E_b\}} \; \text{Annualized Cost}
$$
$$
\text{subject to } \text{hourly physics, storage dynamics, LPSP} \le \varepsilon, \text{ and } P_i, E_b \ge 0.
$$

