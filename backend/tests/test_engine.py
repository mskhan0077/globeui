import pytest
from app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app({"TESTING": True})
    return app.test_client()


def test_health(client):
    r = client.get("/api/health")
    j = r.get_json()
    assert j["ok"] is True
    assert j["islands"] == 37  # 36 Lakshadweep islands + Brest (data/source/extra_places.csv)


def test_evaluate_basic(client):
    r = client.post("/api/evaluate", json={
        "island": "Kadmat",
        "load_kW": 1000,
        "capacities": {
            "wind_kW": 1500, "solar_kWp": 1500,
            "otec_kW": 500, "wave_kW": 0, "bess_kWh": 4000,
        },
    })
    j = r.get_json()
    assert j["ok"], j
    res = j["result"]
    assert res["annual"]["load_kWh"] == pytest.approx(8_760_000, rel=1e-6)
    assert res["econ"]["LCOE_RE_INR_per_kWh"] > 0
    assert 0 <= res["reliability"]["lpsp_monthly"] < 1
    assert res["carbon"]["co2_avoided_t"] > 0
    assert "hourly" in res  # Kadmat has hourly data


def test_optimize_runs(client):
    r = client.post("/api/optimize", json={
        "island": "Kadmat", "load_kW": 1000,
    })
    j = r.get_json()
    assert j["ok"], j
    assert j["result"]["search_size"] > 100

def test_tech_scores_in_range(client):
    r = client.post("/api/evaluate", json={
        "island": "Kadmat",
        "load_kW": 1000,
        "capacities": {
            "wind_kW": 1500, "solar_kWp": 1500,
            "otec_kW": 500, "wave_kW": 0, "bess_kWh": 4000,
        },
    })
    j = r.get_json()
    assert j["ok"], j
    for tech, s in j["result"]["tech_scores"].items():
        for k in ("resource", "capex", "reliability", "sustainability"):
            assert 0 <= s[k] <= 100, (tech, k, s[k])


@pytest.mark.parametrize("island, file_key", [
    ("Parali III", "parali iii"),
    ("South Bangaram Cay", "south bangaram cay"),
    ("Pitti (Kalpeni)", "pitti (kalpeni)"),
    ("Kadmat", "kadmat"),
])
def test_hourly_file_is_the_islands_own(client, island, file_key):
    """Islands whose name contains another island's name must not borrow its hourly file."""
    from app.engine.common import find_hourly_key
    hourly = client.application.config["DATA"]["hourly"]
    assert find_hourly_key(island, {"hourly": hourly}) == file_key


def test_extra_place_brest_evaluates(client):
    r = client.post("/api/evaluate", json={
        "island": "Brest", "load_kW": 1000,
        "capacities": {"wind_kW": 1500, "solar_kWp": 1500, "otec_kW": 0, "wave_kW": 0, "bess_kWh": 4000},
    })
    j = r.get_json()
    assert j["ok"], j
    assert "hourly" in j["result"]  # uses its own 8760 file
    assert j["result"]["econ"]["LCOE_RE_INR_per_kWh"] > 0


def test_volume_discount_factor():
    from app.engine.economics import volume_discount_factor as f
    assert f(0, 500, 0.95) == 1.0
    assert f(500, 500, 0.95) == 1.0                      # single unit: list price
    assert f(1000, 500, 0.95) == pytest.approx((1 + 0.95) / 2)
    assert f(5000, 500, 0.95) < f(2500, 500, 0.95) < 1.0  # more units, bigger discount
    assert f(5000, 500, 1.0) == pytest.approx(1.0)        # eov = 1 disables discount
