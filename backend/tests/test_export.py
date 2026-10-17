import pytest

from app.reports.charts import monthly_balance_svg, nice_ticks
from app.reports.pdf import num_in

MIX = {"wind_kW": 800, "solar_kWp": 1500, "otec_kW": 200, "wave_kW": 100, "bess_kWh": 4000}


@pytest.fixture
def run_id(client):
    r = client.post("/api/evaluate", json={"island": "Kadmat", "load_kW": 1000, "capacities": MIX}).get_json()
    assert r["ok"]
    return r["run_id"]


def test_pdf_export(client, run_id):
    r = client.get(f"/export/pdf/{run_id}")
    assert r.status_code == 200
    assert r.mimetype == "application/pdf"
    assert r.data.startswith(b"%PDF")
    assert "bluegrid_kadmat_" in r.headers["Content-Disposition"]


def test_pdf_ignores_unknown_optimize_run(client, run_id):
    assert client.get(f"/export/pdf/{run_id}?opt=nope").status_code == 200


def test_csv_export_has_wave(client, run_id):
    r = client.get(f"/export/csv/{run_id}")
    assert r.status_code == 200
    header = r.data.decode().splitlines()[0]
    assert "Wave_kWh" in header


def test_unknown_run_is_404(client):
    assert client.get("/export/pdf/missing").status_code == 404
    assert client.get("/export/csv/missing").status_code == 404


def test_indian_grouping():
    assert num_in(1234567) == "12,34,567"
    assert num_in(1234567.891, 2) == "12,34,567.89"
    assert num_in(999) == "999"


def test_monthly_chart_svg():
    monthly = [{"month_num": m, "gen_wind_kWh": 1e5, "gen_fpv_kWh": 2e5, "gen_otec_kWh": 0.0,
                "gen_wave_kWh": 0.0, "load_kWh": 7.44e5} for m in range(1, 13)]
    svg = monthly_balance_svg(monthly)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert "Dec" in svg and "Demand" in svg
    assert nice_ticks(744)[-1] >= 744
