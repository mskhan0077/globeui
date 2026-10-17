import re
from pathlib import Path
from urllib.parse import urlparse

import openpyxl

from app.references import REFERENCES, anchor, citations

ROOT = Path(__file__).resolve().parents[2]
WORKBOOK = ROOT / "data/source/BlueGrid_Lakshadweep_Dummy_Data.xlsx"


def test_references_page(client):
    r = client.get("/references")
    assert r.status_code == 200
    html = r.data.decode()
    for ref in REFERENCES:
        assert f'id="{anchor(ref["key"])}"' in html
    assert "Renewable Power Generation Costs in 2023" in html


def test_references_api(client):
    j = client.get("/api/references").get_json()
    assert j["ok"] and j["citations"] == citations()
    assert j["citations"]["irena-costs-2023"] == {"label": "IRENA, 2024", "href": "/references#ref-irena-costs-2023"}


def test_keys_are_unique():
    keys = [r["key"] for r in REFERENCES]
    assert len(keys) == len(set(keys))


def test_every_cited_key_exists():
    """Keys cited in the globe's facts and the planner's KPI boxes must be in the list,
    or the citation silently disappears."""
    text = (ROOT / "frontend/js/config.js").read_text(encoding="utf-8")
    facts = text[text.index("export const FACTS"):]
    cited = {k.strip() for m in re.findall(r"\{([a-z0-9,\- ]+)\}", facts) for k in m.split(",")}
    info = (ROOT / "backend/app/static/js/info-content.js").read_text(encoding="utf-8")
    kpi_refs = re.findall(r"refs: \[([^\]]*)\]", info)
    assert len(kpi_refs) >= 9, "every KPI box should cite its definition"
    cited |= {k for m in kpi_refs for k in re.findall(r'"([^"]+)"', m)}
    assert cited, "no citations found"
    assert cited <= set(citations()), f"unknown reference keys: {sorted(cited - set(citations()))}"


def test_no_reference_comes_from_the_dataset():
    """References must be independent of BlueGrid's own dataset: none of its source links."""
    ws = openpyxl.load_workbook(WORKBOOK, read_only=True)["Sources"]
    dataset_urls = {str(c).strip().rstrip("/") for row in ws.iter_rows(values_only=True)
                    for c in row if isinstance(c, str) and c.startswith("http")}
    dataset_hosts = {urlparse(u).netloc for u in dataset_urls}
    for ref in REFERENCES:
        assert ref["url"].rstrip("/") not in dataset_urls, ref["key"]
        # the same publication on the same site counts too (e.g. a different page of it)
        same_site = urlparse(ref["url"]).netloc in dataset_hosts
        assert not (same_site and any(ref["title"].lower()[:30] in u.lower() for u in dataset_urls)), ref["key"]
