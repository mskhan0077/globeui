"""The literature behind BlueGrid's figures, numbered like a research paper.

One list for the whole site: the /references page shows it, and /api/references gives
the numbers to the planner's (i) boxes and the globe's fact bubbles, which cite by key,
e.g. [1] or [3, 4]. Numbers follow the order below, so add new entries at the end to
keep existing numbers stable.
"""
from __future__ import annotations

REFERENCES: list[dict] = [
    {
        "key": "irena-costs-2023",
        "authors": "IRENA",
        "year": "2024",
        "title": "Renewable Power Generation Costs in 2023",
        "source": "International Renewable Energy Agency, Abu Dhabi",
        "url": "https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2024/Sep/IRENA_Renewable_power_generation_costs_in_2023.pdf",
    },
    {
        "key": "ipcc-ar5-annex3",
        "authors": "Schlömer, S., Bruckner, T., Fulton, L., Hertwich, E., McKinnon, A., Perczyk, D., Roy, J., Schaeffer, R., Sims, R., Smith, P., & Wiser, R.",
        "year": "2014",
        "title": "Annex III: Technology-specific cost and performance parameters",
        "source": "In Climate Change 2014: Mitigation of Climate Change. Contribution of Working Group III to the Fifth Assessment Report of the IPCC. Cambridge University Press",
        "url": "https://www.ipcc.ch/report/ar5/wg3/",
    },
    {
        "key": "ipcc-2006-combustion",
        "authors": "IPCC",
        "year": "2006",
        "title": "2006 IPCC Guidelines for National Greenhouse Gas Inventories, Volume 2: Energy, Chapter 2: Stationary Combustion",
        "source": "Institute for Global Environmental Strategies (IGES), Hayama, Japan",
        "url": "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf",
    },
    {
        "key": "lok-sabha-pac-2022",
        "authors": "Public Accounts Committee",
        "year": "2022",
        "title": "Generation and Distribution of Power in Lakshadweep Islands (46th Report, 17th Lok Sabha)",
        "source": "Lok Sabha Secretariat, New Delhi",
        "url": "https://eparlib.nic.in/bitstream/123456789/845632/1/17_Public_Accounts_46.pdf",
    },
    {
        "key": "bluegrid-kadmat",
        "authors": "BlueGrid",
        "year": "2026",
        "title": "Least-cost renewable mix for Kadmat at 1 MW demand, compared with diesel only",
        "source": "Authors’ calculation with the BlueGrid planner (25-year nominal discounted cash flow)",
        "url": "/planner?island=Kadmat",
    },
    {
        "key": "kerc-wind-2026",
        "authors": "Wind Insider",
        "year": "2026",
        "title": "KERC sets ₹3.24/unit ceiling tariff for wind projects for FY27–FY29 in Karnataka",
        "source": "Wind Insider, 5 May 2026",
        "url": "https://windinsider.com/2026/05/05/kerc-sets-%e2%82%b93-24-unit-ceiling-tariff-for-wind-projects-for-fy27-fy29-in-karnataka/",
    },
    {
        "key": "ctuil-benchmarks-2026",
        "authors": "Energetica India",
        "year": "2026",
        "title": "CTUIL revises benchmark costs, land requirements for solar, wind and BESS projects",
        "source": "Energetica India, September 2026",
        "url": "https://www.energetica-india.net/news/ctuil-revises-benchmark-costs-land-requirements-for-solar-wind-and-bess-projects",
    },
    {
        "key": "giz-floating-pv-2024",
        "authors": "pv magazine India",
        "year": "2024",
        "title": "New study calculates 207 GWp of floating solar potential in India (MNRE / GIZ IN-Solar study)",
        "source": "pv magazine India, 9 May 2024",
        "url": "https://www.pv-magazine-india.com/2024/05/09/new-study-shows-207-gwp-of-floating-solar-potential-in-india",
    },
    {
        "key": "ember-bess-2025",
        "authors": "Ember",
        "year": "2025",
        "title": "Batteries now cheap enough to deliver solar when it is needed",
        "source": "Ember, December 2025",
        "url": "https://ember-energy.org/latest-updates/batteries-now-cheap-enough-to-deliver-solar-when-it-is-needed/",
    },
    {
        "key": "irena-otec-2014",
        "authors": "Kempener, R., & Neumann, F.",
        "year": "2014",
        "title": "Ocean Thermal Energy Conversion: Technology Brief (Ocean Energy Technology Brief 1)",
        "source": "International Renewable Energy Agency, Abu Dhabi",
        "url": "https://www.irena.org/publications/2014/Jun/Ocean-Thermal-Energy-Conversion",
    },
    {
        "key": "oes-lcoe-2015",
        "authors": "Ocean Energy Systems",
        "year": "2015",
        "title": "International Levelised Cost of Energy for Ocean Energy Technologies",
        "source": "IEA Technology Collaboration Programme for Ocean Energy Systems",
        "url": "https://www.ocean-energy-systems.org/publications/oes-documents/market-policy-/document/international-levelised-cost-of-energy-for-ocean-energy-technologies-2015-/",
    },
    {
        "key": "wave-india-2025",
        "authors": "Sathyanarayana, A., & Seelam, J.",
        "year": "2025",
        "title": "Wave energy potential along the Indian coast: A comprehensive review",
        "source": "Ocean Engineering, 316, 120033",
        "url": "https://doi.org/10.1016/j.oceaneng.2024.120033",
    },
    {
        "key": "pm-ssy-2026",
        "authors": "Indian Infrastructure",
        "year": "2026",
        "title": "Cabinet approves Rs 50.7 billion scheme to promote floating solar projects (PM Surya Sarovar Yojana)",
        "source": "Indian Infrastructure, 4 August 2026",
        "url": "https://indianinfrastructure.com/2026/08/04/cabinet-approves-rs-50-7-billion-scheme-to-promote-floating-solar-projects/",
    },
    {
        "key": "bess-vgf-2025",
        "authors": "SolarQuarter",
        "year": "2025",
        "title": "Ministry of Power launches ₹5,400 crore VGF scheme to boost 30 GWh battery energy storage capacity",
        "source": "SolarQuarter, 10 June 2025",
        "url": "https://solarquarter.com/2025/06/10/ministry-of-power-launches-%E2%82%B95400-crore-vgf-scheme-to-boost-30-gwh-battery-energy-storage-capacity/",
    },
    {
        "key": "era5-2020",
        "authors": "Hersbach, H., Bell, B., Berrisford, P., et al.",
        "year": "2020",
        "title": "The ERA5 global reanalysis",
        "source": "Quarterly Journal of the Royal Meteorological Society, 146(730), 1999–2049",
        "url": "https://doi.org/10.1002/qj.3803",
    },
    {
        "key": "open-meteo-2023",
        "authors": "Zippenfenig, P.",
        "year": "2023",
        "title": "Open-Meteo.com Weather API [Computer software]",
        "source": "Zenodo",
        "url": "https://doi.org/10.5281/zenodo.7970649",
    },
    {
        "key": "global-wind-atlas-2023",
        "authors": "Davis, N. N., Badger, J., Hahmann, A. N., et al.",
        "year": "2023",
        "title": "The Global Wind Atlas: A high-resolution dataset of climatologies and associated web-based application",
        "source": "Bulletin of the American Meteorological Society, 104(8), E1507–E1525",
        "url": "https://doi.org/10.1175/BAMS-D-21-0075.1",
    },
    {
        "key": "global-solar-atlas-2019",
        "authors": "ESMAP",
        "year": "2019",
        "title": "Global Solar Atlas 2.0: Technical Report",
        "source": "Energy Sector Management Assistance Program, World Bank, Washington, DC",
        "url": "https://documents.worldbank.org/curated/en/529431592893043403",
    },
]

_NUMBER = {ref["key"]: i + 1 for i, ref in enumerate(REFERENCES)}


def numbered() -> list[dict]:
    """REFERENCES with their citation number ("n")."""
    return [{**ref, "n": _NUMBER[ref["key"]]} for ref in REFERENCES]


def numbers() -> dict[str, int]:
    """key → citation number, for the front ends."""
    return dict(_NUMBER)
