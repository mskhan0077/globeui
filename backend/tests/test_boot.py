def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    j = r.get_json()
    assert j["ok"] is True
    assert j["islands"] > 0
    assert 0.13 < j["crf"] < 0.15   # CRF at the nominal rate: (1.08 × 1.05 − 1 = 13.4%, 25 yr) ≈ 0.140

def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"BlueGrid" in r.data


def test_globe_served_at_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b'id="globeViz"' in r.data
    assert client.get("/js/main.js").status_code == 200


def test_classic_planner_page(client):
    r = client.get("/planner")
    assert r.status_code == 200
    assert b'id="sliders"' in r.data


def test_planner_embedded_for_an_island(client):
    r = client.get("/planner?embed=1&island=Agatti")
    assert r.status_code == 200
    assert b'class="embed"' in r.data
    assert b'class="menubar"' not in r.data
    assert b'<option value="Agatti" selected>' in r.data


def test_standalone_planner_has_menubar_and_backdrop(client):
    r = client.get("/planner?island=Agatti")
    assert b'class="menubar"' in r.data
    assert b'id="backdrop"' in r.data
    assert b'"Agatti": [' in r.data  # island coordinates for the backdrop
    assert client.get("/css/menubar.css").status_code == 200


def test_tech_params_endpoint(client):
    j = client.get("/api/tech").get_json()
    assert j["ok"] is True
    for name in ("Wind", "Floating Solar PV", "OTEC", "Wave", "BESS"):
        assert j["tech"][name]["capex_island_INR"] > 0
        assert j["tech"][name]["lifetime_yr"] > 0


def test_finance_params_endpoint(client):
    f = client.get("/api/finance").get_json()["finance"]
    for key in ("discount_rate_real", "project_life_yr", "diesel_fuel_cost_INR_per_kWh",
                "diesel_emission_factor_tCO2_per_MWh", "carbon_price_INR_per_t"):
        assert key in f
