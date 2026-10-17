"""Shared island matching, localized costs, and BESS constants."""
from __future__ import annotations

SELF_DISCHARGE_PER_HOUR = 0.0001

def normalize_island(island: str) -> str:
    return str(island).replace("_", " ").strip().lower()

def find_hourly_key(island: str, dfs: dict):
    """Key of the island's 8760 hourly file, or None.

    Exact name first: a substring match alone would give e.g. "Parali III" the
    "parali ii" file, or "South Bangaram Cay" the "bangaram" file.
    """
    hourly = dfs.get("hourly")
    if not hourly:
        return None
    target = normalize_island(island)
    norm = {key: normalize_island(key) for key in hourly}
    exact = next((key for key, cand in norm.items() if cand == target), None)
    if exact is not None:
        return exact
    return next((key for key, cand in norm.items() if target in cand or cand in target), None)

def localize_tech(tech, island: str):
    localized = tech.copy()
    norm = normalize_island(island)
    if "france" in norm or "brest" in norm:
        if "capex_island_INR" in localized.columns:
            localized["capex_island_INR"] = localized["capex_island_INR"] * 2.5
        if "opex_INR_per_unit_yr" in localized.columns:
            localized["opex_INR_per_unit_yr"] = localized["opex_INR_per_unit_yr"] * 2.5
    return localized