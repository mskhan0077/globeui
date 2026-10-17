import re
from pathlib import Path

from app.references import REFERENCES, numbers

ROOT = Path(__file__).resolve().parents[2]


def test_references_page(client):
    r = client.get("/references")
    assert r.status_code == 200
    html = r.data.decode()
    assert 'id="ref-1"' in html and f'id="ref-{len(REFERENCES)}"' in html
    assert "Renewable Power Generation Costs in 2023" in html


def test_references_api(client):
    j = client.get("/api/references").get_json()
    assert j["ok"] and j["numbers"] == numbers()
    assert sorted(j["numbers"].values()) == list(range(1, len(REFERENCES) + 1))


def test_keys_are_unique():
    keys = [r["key"] for r in REFERENCES]
    assert len(keys) == len(set(keys))


def test_every_cited_key_exists():
    """Keys cited by the front ends must be in the list, or the citation silently disappears."""
    known = set(numbers())
    sources = {
        ROOT / "frontend/js/config.js": r"\{([a-z0-9,\- ]+)\}",              # {key} / {k1,k2} in FACTS
        ROOT / "backend/app/static/js/info-content.js": r'"([a-z0-9]+(?:-[a-z0-9]+)+)"',
    }
    cited = set()
    for path, pattern in sources.items():
        text = path.read_text(encoding="utf-8")
        if path.name == "config.js":
            text = text[text.index("export const FACTS"):]
        for m in re.findall(pattern, text):
            cited.update(k.strip() for k in m.split(","))
    cited = {k for k in cited if re.search(r"\d{4}|annex|kadmat", k)}  # reference keys carry a year/tag
    assert cited, "no citations found"
    assert cited <= known, f"unknown reference keys: {sorted(cited - known)}"
