"""Carbon accounting."""
from __future__ import annotations


def carbon_metrics(delivered_kWh: float, finance: dict) -> dict:
    """CO2 avoided (only delivered RE displaces diesel)."""
    ef = float(finance["diesel_emission_factor_tCO2_per_MWh"])
    price = float(finance["carbon_price_INR_per_t"])
    sfc = float(finance["diesel_sfc_L_per_kWh"])

    co2_t = delivered_kWh / 1000.0 * ef
    credit_INR = co2_t * price
    diesel_liters = delivered_kWh * sfc

    return {
        "co2_avoided_t": co2_t,
        "carbon_credit_INR": credit_INR,
        "diesel_avoided_L": diesel_liters,
    }