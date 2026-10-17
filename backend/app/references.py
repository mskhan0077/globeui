"""Published sources for facts and KPI definitions shown on the BlueGrid site, cited
author–date style: research papers and government publications.

Only independent literature goes here, never the sources of BlueGrid's own dataset.
The /references page lists them alphabetically; /api/references gives the front ends a
short label and a link for each key, so text can cite e.g. "(IRENA, 2024)" with the
words linking to the entry on the References page.
"""
from __future__ import annotations

REFERENCES: list[dict] = [
    {
        "key": "irena-costs-2023",
        "cite": "IRENA, 2024",
        "authors": "International Renewable Energy Agency (IRENA)",
        "year": "2024",
        "title": "Renewable Power Generation Costs in 2023",
        "source": "IRENA, Abu Dhabi",
        "url": "https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2024/Sep/IRENA_Renewable_power_generation_costs_in_2023.pdf",
    },
    {
        "key": "owid-safest-cleanest",
        "cite": "Ritchie, 2024",
        "authors": "Ritchie, H.",
        "year": "2024",
        "title": "What are the safest and cleanest sources of energy?",
        "source": "Our World in Data (carbon intensity figures updated March 2024; life-cycle data from UNECE and Turconi et al.)",
        "url": "https://ourworldindata.org/safest-sources-of-energy",
    },
    {
        "key": "seforall-sids-2012",
        "cite": "SEforALL, 2012",
        "authors": "Sustainable Energy for All (SEforALL)",
        "year": "2012",
        "title": "Twenty Small Island Developing States announce new actions that reduce dependence on fossil fuels and end poverty (Barbados Declaration)",
        "source": "SEforALL, 8 May 2012",
        "url": "https://www.seforall.org/news/twenty-small-island-developing-states-announce-new-actions-that-reduce-dependence-on-fossil",
    },

    # ---------- KPI definitions (planner (i) boxes) ----------
    {
        "key": "eia-lcoe-2025",
        "cite": "EIA, 2025",
        "authors": "U.S. Energy Information Administration (EIA)",
        "year": "2025",
        "title": "Levelized Costs of New Generation Resources in the Annual Energy Outlook 2025",
        "source": "EIA, Washington, DC, April 2025",
        "url": "https://www.eia.gov/outlooks/aeo/electricity_generation/pdf/AEO2025_LCOE_report.pdf",
    },
    {
        "key": "eia-capital-cost-2024",
        "cite": "EIA, 2024",
        "authors": "U.S. Energy Information Administration (EIA)",
        "year": "2024",
        "title": "Capital Cost and Performance Characteristics for Utility-Scale Electric Power Generating Technologies",
        "source": "Prepared by Sargent & Lundy for EIA, Washington, DC, February 2024",
        "url": "https://www.eia.gov/analysis/studies/powerplants/capitalcost/pdf/capital_cost_AEO2025.pdf",
    },
    {
        "key": "eia-capacity-factor",
        "cite": "EIA, n.d.",
        "authors": "U.S. Energy Information Administration (EIA)",
        "year": "n.d.",
        "title": "Glossary: Capacity factor",
        "source": "EIA, Washington, DC",
        "url": "https://www.eia.gov/tools/glossary/index.php?id=Capacity_factor",
    },
    {
        "key": "short-1995",
        "cite": "Short et al., 1995",
        "authors": "Short, W., Packey, D. J., & Holt, T.",
        "year": "1995",
        "title": "A Manual for the Economic Evaluation of Energy Efficiency and Renewable Energy Technologies",
        "source": "National Renewable Energy Laboratory (U.S. Department of Energy), Golden, CO, NREL/TP-462-5173",
        "url": "https://www.osti.gov/biblio/35391",
    },
    {
        "key": "omb-a94-2023",
        "cite": "OMB, 2023",
        "authors": "Office of Management and Budget (OMB)",
        "year": "2023",
        "title": "Circular A-94: Guidelines and Discount Rates for Benefit-Cost Analysis of Federal Programs",
        "source": "Executive Office of the President, Washington, DC, November 2023 (section on real versus nominal discount rates)",
        "url": "https://www.whitehouse.gov/wp-content/uploads/2023/11/CircularA-94.pdf",
    },
    {
        "key": "borowy-1996",
        "cite": "Borowy & Salameh, 1996",
        "authors": "Borowy, B. S., & Salameh, Z. M.",
        "year": "1996",
        "title": "Methodology for optimally sizing the combination of a battery bank and PV array in a wind/PV hybrid system",
        "source": "IEEE Transactions on Energy Conversion, 11(2), 367–375",
        "url": "https://doi.org/10.1109/60.507648",
    },
    {
        "key": "yang-2007",
        "cite": "Yang et al., 2007",
        "authors": "Yang, H., Lu, L., & Zhou, W.",
        "year": "2007",
        "title": "A novel optimization sizing model for hybrid solar-wind power generation system",
        "source": "Solar Energy, 81(1), 76–84",
        "url": "https://doi.org/10.1016/j.solener.2006.06.010",
    },
    {
        "key": "ipcc-2006-combustion",
        "cite": "IPCC, 2006",
        "authors": "Intergovernmental Panel on Climate Change (IPCC)",
        "year": "2006",
        "title": "2006 IPCC Guidelines for National Greenhouse Gas Inventories, Volume 2: Energy, Chapter 2: Stationary Combustion",
        "source": "Institute for Global Environmental Strategies (IGES), Hayama, Japan (Table 2.2: default CO₂ emission factors)",
        "url": "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf",
    },
]


def anchor(key: str) -> str:
    """Element id of a reference on the References page."""
    return f"ref-{key}"


def alphabetical() -> list[dict]:
    """REFERENCES sorted by author then year, with their page anchor."""
    refs = sorted(REFERENCES, key=lambda r: (r["authors"].lower(), r["year"]))
    return [{**r, "anchor": anchor(r["key"])} for r in refs]


def citations() -> dict[str, dict]:
    """key → {"label": "IRENA, 2024", "href": "/references#ref-…"}, for the front ends."""
    return {r["key"]: {"label": r["cite"], "href": f"/references#{anchor(r['key'])}"} for r in REFERENCES}
