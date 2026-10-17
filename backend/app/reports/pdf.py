"""PDF report: turns an evaluate() result into report.html and renders it with WeasyPrint."""
from __future__ import annotations

import base64
import math
from datetime import date
from pathlib import Path

from flask import render_template
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from ..config import APP_DEFAULTS
from ..references import alphabetical, citations
from .charts import MONTHS as MONTH_NAMES, TECHS, monthly_balance_svg

STATIC = Path(__file__).resolve().parents[1] / "static"
REPORT_CSS = STATIC / "css" / "report.css"

# Short definitions for the report's last section, with reference keys (references.py)
DEFINITIONS = [
    ("LCOE", "Levelised cost of the renewable energy delivered: the yearly cost of capital and O&M ÷ energy delivered.", ["eia-lcoe-2025", "short-1995"]),
    ("System cost", "Like LCOE, but including diesel fuel for unmet demand, divided by the whole demand.", ["short-1995", "eia-lcoe-2025"]),
    ("Nominal discount rate", "(1 + real rate) × (1 + inflation) − 1; discounts costs that include inflation.", ["omb-a94-2023", "short-1995"]),
    ("PLF", "Energy delivered ÷ (target load × hours in the year).", ["eia-capacity-factor"]),
    ("LPSP", "Loss of power supply probability: unmet energy ÷ total demand.", ["borowy-1996", "yang-2007"]),
    ("CO₂ avoided", "Diesel energy displaced × the diesel emission factor.", ["ipcc-2006-combustion"]),
    ("CAPEX and volume discount", "Upfront investment; each doubling of identical units cuts the next unit’s price by the economies-of-volume factor.", ["eia-capital-cost-2024", "oconnor-2013"]),
]

SCORE_CRITERIA = [("resource", "Resource"), ("capex", "CAPEX"),
                  ("reliability", "Reliability"), ("sustainability", "Sustainability")]


# ---------- number formatting (Indian digit grouping, like the planner) ----------

def num_in(x: float, d: int = 0) -> str:
    """12,34,567 or 12,34,567.89"""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "–"
    whole, _, frac = f"{abs(x):.{d}f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        whole = ",".join([head[max(i - 2, 0):i] for i in range(len(head), 0, -2)][::-1]) + "," + tail
    return ("-" if x < 0 and float(f"{x:.{d}f}") != 0 else "") + whole + (f".{frac}" if frac else "")


def crore(x: float, d: int = 2) -> str:
    return f"₹{x / 1e7:,.{d}f} Cr"


def pct(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f}%"


def _ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))


# ---------- context ----------

def build_context(res: dict, site: dict, finance: dict, ranked: list[dict] | None,
                  minimums: dict | None = None) -> dict:
    caps, econ, carbon, rel, annual = (res["capacities"], res["econ"], res["carbon"],
                                       res["reliability"], res["annual"])
    hourly = rel.get("lpsp_hourly") is not None
    lpsp = rel.get("lpsp_hourly", rel.get("lpsp_annual", rel.get("lpsp_monthly", 0.0)))
    load_kW = caps["load_kW"]
    gen_total = annual["gen_total_kWh"] or 0.0

    kpis = [
        {"label": "LCOE (RE only)", "value": f"₹{econ['LCOE_RE_INR_per_kWh']:.2f}", "sub": "per kWh delivered"},
        {"label": "System cost", "value": f"₹{econ['cost_of_service_INR_per_kWh']:.2f}", "sub": "per kWh, incl. diesel top-up"},
        {"label": "LPSP", "value": pct(lpsp, 2), "sub": "hourly simulation" if hourly else "annual (monthly data)"},
        {"label": "PLF vs target", "value": pct(res["plf_target"]), "sub": f"{num_in(annual['delivered_kWh'] / 1000)} MWh served / yr"},
        {"label": "CO₂ avoided", "value": f"{num_in(carbon['co2_avoided_t'])} t", "sub": f"per year · credit ₹{num_in(carbon['carbon_credit_INR'])}"},
        {"label": "CAPEX", "value": crore(econ["capex_INR"], 1), "sub": "island-adjusted, after volume discount"},
        {"label": "Nominal rate", "value": pct(econ.get("nominal_discount_rate", 0.0), 2), "sub": "discount rate incl. inflation"},
        {"label": "Unmet", "value": f"{num_in(annual['unmet_kWh'] / 1000)} MWh", "sub": "per year, diesel top-up"},
    ]

    mix = []
    for t in TECHS:
        cap = caps.get(t["cap"], 0.0)
        g = annual.get(f"gen_{t['key']}_kWh", 0.0)
        mix.append({
            "name": t["name"], "color": t["color"], "capacity": f"{num_in(cap)} kW",
            "capex": crore(res["capex"].get(t["cap"], 0.0)) if cap else "–",
            "gen": num_in(g / 1000) if cap else "–",
            "cf": pct(g / (cap * annual["hours"])) if cap else "–",
            "share": g / gen_total if gen_total else 0.0, "active": cap > 0,
        })
    battery = {"capacity": f"{num_in(caps['bess_kWh'])} kWh",
               "capex": crore(res["capex"].get("bess_kWh", 0.0)) if caps["bess_kWh"] else "–",
               "hours": caps["bess_kWh"] / load_kW if load_kW else 0.0, "active": caps["bess_kWh"] > 0}

    scores = []
    for t in TECHS:
        s = res.get("tech_scores", {}).get(t["score_key"])
        if s:
            scores.append({"name": t["name"], "color": t["color"],
                           "cells": [max(0.0, min(100.0, float(s.get(k, 0.0)))) for k, _ in SCORE_CRITERIA]})

    active = [m["name"].lower() if m["name"] != "OTEC" else "OTEC" for m in mix if m["active"]]
    mix_text = ", ".join(active[:-1]) + (" and " if len(active) > 1 else "") + active[-1] if active else "No renewables"
    if battery["active"]:
        mix_text += f" with {battery['hours']:.1f} h of battery storage"
    headline = (f"{mix_text[0].upper()}{mix_text[1:]} covers <strong>{pct(1 - lpsp)}</strong> of a "
                f"{num_in(load_kW)} kW demand, at <strong>₹{econ['LCOE_RE_INR_per_kWh']:.2f}/kWh</strong> "
                f"for the renewable energy and ₹{econ['cost_of_service_INR_per_kWh']:.2f}/kWh including diesel top-up.")

    # Inflation inputs of the nominal DCF model, with economics.py's defaults
    infl = {k: float(finance.get(f"inflation_rate_{k}", d))
            for k, d in (("general", 0.05), ("opex", 0.04), ("diesel", 0.07), ("bess", -0.05))}
    r_nom = econ.get("nominal_discount_rate", (1 + finance["discount_rate_real"]) * (1 + infl["general"]) - 1)

    vd = res.get("volume_discount", {}).values()
    saving = sum(d["list_INR"] - d["discounted_INR"] for d in vd)

    economics = [
        ("Total CAPEX (after volume discount)", crore(econ["capex_INR"] + econ.get("subsidy_INR", 0.0))),
        ("Volume discount (bulk purchase)", f"− {crore(saving)}" if saving > 0 else "none"),
        ("Subsidies", f"− {crore(econ['subsidy_INR'])}" if econ.get("subsidy_INR") else "none"),
        (f"Battery replacement (year {finance.get('bess_replacement_year', 15):.0f}, present value)", crore(econ.get("bess_repl_pv_INR", 0.0))),
        (f"Annualised capital (CRF {econ['crf']:.4f})", f"{crore(econ['annualized_capital_INR'])} / yr"),
        ("Operation & maintenance (year 1)", f"{crore(econ['opex_annual_INR'])} / yr"),
        ("Diesel fuel for unmet demand (levelised)", f"{crore(econ['diesel_fuel_cost_INR'])} / yr"),
    ]
    energy = [
        ("Demand", f"{num_in(annual['load_kWh'] / 1000)} MWh"),
        ("Renewable generation", f"{num_in(gen_total / 1000)} MWh"),
        ("Delivered to load", f"{num_in(annual['delivered_kWh'] / 1000)} MWh"),
        ("Surplus (stored or curtailed)", f"{num_in(annual['surplus_kWh'] / 1000)} MWh"),
        ("Unmet (diesel top-up)", f"{num_in(annual['unmet_kWh'] / 1000)} MWh"),
    ]
    if hourly and res.get("hourly", {}).get("lole_hours") is not None:
        energy.append(("Hours with unmet demand", f"{num_in(res['hourly']['lole_hours'])} h"))

    f = finance
    assumptions = [
        ("Discount rate (real)", pct(f["discount_rate_real"], 0)),
        ("General inflation", pct(infl["general"], 0)),
        ("Nominal discount rate", pct(r_nom, 2)),
        ("Project life", f"{f['project_life_yr']:.0f} years"),
        ("Diesel fuel cost (year 1)", f"₹{f['diesel_fuel_cost_INR_per_kWh']:.0f} / kWh"),
        ("Diesel price escalation", f"{pct(infl['diesel'], 0)} / yr"),
        ("O&M cost escalation", f"{pct(infl['opex'], 0)} / yr"),
        ("Battery price change", f"{pct(infl['bess'], 0)} / yr"),
        ("Diesel emission factor", f"{f['diesel_emission_factor_tCO2_per_MWh']:.3f} tCO₂/MWh"),
        ("Carbon price", f"₹{num_in(f['carbon_price_INR_per_t'])} / t"),
        ("Battery round-trip efficiency", pct(f["bess_round_trip_eff"], 0)),
        ("Battery usable depth, max C-rate", f"{pct(f['bess_depth_of_discharge'], 0)}, {f['bess_max_c_rate']:.1f}C"),
        ("Subsidies", "applied" if f.get("apply_subsidies_flag", 0) > 0.5 else "not applied"),
        ("Resource data", f"hourly ({res.get('timezone') or 'local time'})" if hourly else "monthly averages"),
    ]

    site_facts = [("Coordinates", f"{abs(site['lat']):.3f}° {'N' if site['lat'] >= 0 else 'S'}, "
                                  f"{abs(site['lon']):.3f}° {'E' if site['lon'] >= 0 else 'W'}")]
    if _ok(site.get("population")):
        site_facts.append(("Population (2011)", num_in(site["population"])))
    if _ok(site.get("land_area")):
        site_facts.append(("Land area", f"{site['land_area']:.2f} km²"))

    ranked_rows = []
    for i, r in enumerate((ranked or [])[:5]):
        c = r["capacities"]
        ranked_rows.append({
            "rank": i + 1,
            "mix": " / ".join(num_in(c.get(t["cap"], 0)) for t in TECHS),
            "bess": num_in(c.get("bess_kWh", 0)),
            "lcoe": f"₹{r['lcoe']:.2f}", "coverage": pct(r["coverage"]),
            "capex": crore(r["capex_INR"], 1),
            "applied": all(abs(c.get(k, 0) - caps.get(k, 0)) < 1e-6
                           for k in ("wind_kW", "solar_kWp", "otec_kW", "wave_kW", "bess_kWh")),
        })

    # ---------- data statistics ----------
    stat_rows = []
    for key, label in (("wind", "Wind"), ("solar", "Floating solar"), ("otec", "OTEC"), ("wave", "Wave"), ("load", "Load")):
        st = (res.get("stats") or {}).get(key)
        if st and (key == "load" or st["max"] > 0):
            stat_rows.append({"name": label, "cells": [f"{st[k]:,.1f}" for k in ("mean", "median", "std", "min", "max")]})
    resource_rows = []
    for t in TECHS:
        sc = res.get("tech_scores", {}).get(t["score_key"])
        if sc:
            resource_rows.append({"name": t["name"], "color": t["color"], "cells": [
                pct(sc["cf_annual"]), pct(sc["firmness"] * sc["cf_annual"]), pct(sc["cf_min"]), pct(sc["cf_max"])]})

    # ---------- CAPEX and the volume (bulk) discount ----------
    discount_rows = []
    for t in TECHS + [{"cap": "bess_kWh", "name": "Battery storage", "color": None}]:
        d = (res.get("volume_discount") or {}).get(t["cap"])
        if d and d["list_INR"] > 0:
            discount_rows.append({
                "name": t["name"], "color": t.get("color"),
                "units": f"{d['units']:.1f} × {num_in(d['unit_size'])} {d['unit_basis']}",
                "list": crore(d["list_INR"]), "pct": pct(d["discount_pct"]),
                "saving": crore(d["list_INR"] - d["discounted_INR"]), "net": crore(d["discounted_INR"]),
            })
    if discount_rows:
        list_total = sum(d["list_INR"] for d in res["volume_discount"].values())
        net_total = sum(d["discounted_INR"] for d in res["volume_discount"].values())
        discount_total = {"list": crore(list_total), "saving": crore(list_total - net_total), "net": crore(net_total),
                          "pct": pct(1 - net_total / list_total) if list_total else "–"}
    else:
        discount_total = None

    # ---------- months where generation falls short of the load ----------
    deficit_months = [MONTH_NAMES[int(m["month_num"]) - 1] for m in sorted(res["monthly"], key=lambda m: m["month_num"])
                      if m.get("gen_total_kWh", 0) < m["load_kWh"]]

    # ---------- minimum shares used by Find optimal mix ----------
    names = {"min_wind_pct": "wind", "min_solar_pct": "floating solar", "min_otec_pct": "OTEC", "min_wave_pct": "wave"}
    minimums_text = ", ".join(f"{names[k]} ≥ {v * 100:.0f}% of the load" for k, v in (minimums or {}).items() if k in names)

    # ---------- definitions, with their references (research papers / government) ----------
    cites = citations()
    definitions = [
        {"term": term, "text": text, "refs": [cites[k]["label"] for k in keys if k in cites]}
        for term, text, keys in DEFINITIONS
    ]
    ref_keys = [k for _, _, keys in DEFINITIONS for k in keys]
    references = [r for r in alphabetical() if r["key"] in ref_keys]

    svg = monthly_balance_svg(res["monthly"])
    return {
        "island": res["island"], "group": site.get("group"), "today": date.today().strftime("%d %B %Y"),
        "load_kW": num_in(load_kW), "headline": headline, "kpis": kpis, "mix": mix, "battery": battery,
        "monthly_svg": base64.b64encode(svg.encode()).decode(), "criteria": [c for _, c in SCORE_CRITERIA],
        "scores": scores, "economics": economics, "energy": energy, "assumptions": assumptions,
        "site": site_facts, "ranked": ranked_rows, "minimums": minimums_text,
        "stat_rows": stat_rows, "resource_rows": resource_rows,
        "resource_basis": "hourly data" if hourly else "monthly averages",
        "discount_rows": discount_rows, "discount_total": discount_total, "deficit_months": deficit_months,
        "definitions": definitions, "references": references,
        "lpsp_target": pct(APP_DEFAULTS["reliability_target_lpsp"], 0),
    }


def render_pdf(ctx: dict) -> bytes:
    html = render_template("report/report.html", **ctx)
    fonts = FontConfiguration()  # needed for report.css's @font-face (bundled Inter)
    css = CSS(filename=str(REPORT_CSS), font_config=fonts)
    return HTML(string=html, base_url=str(STATIC)).write_pdf(stylesheets=[css], font_config=fonts)
