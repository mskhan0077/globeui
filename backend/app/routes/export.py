"""CSV and PDF export routes (for a run cached by /api/evaluate)."""
import csv
import io

from flask import Blueprint, Response, current_app, request

from app.reports.pdf import build_context, render_pdf

bp = Blueprint("export", __name__)


def _cached_run(run_id):
    return current_app.config.get("CACHE", {}).get(run_id)


def _filename(res, run_id, ext):
    slug = "".join(ch if ch.isalnum() else "_" for ch in res["island"].lower())
    return f"bluegrid_{slug}_{run_id[:6]}.{ext}"


@bp.get("/csv/<run_id>")
def export_csv(run_id):
    res = _cached_run(run_id)
    if res is None:
        return "Run not found or expired. Please evaluate again.", 404

    buf = io.StringIO()
    w = csv.writer(buf)

    # Monthly table
    w.writerow(["Month", "Hours", "Wind_kWh", "FPV_kWh", "OTEC_kWh", "Wave_kWh",
                "Total_kWh", "Load_kWh", "Delivered_kWh", "Unmet_kWh", "Coverage"])
    for row in res["monthly"]:
        w.writerow([
            row["month_num"], row["hours"], row["gen_wind_kWh"], row["gen_fpv_kWh"],
            row["gen_otec_kWh"], row.get("gen_wave_kWh", 0.0), row["gen_total_kWh"], row["load_kWh"],
            row["delivered_kWh"], row["unmet_kWh"], row["coverage"]
        ])

    # Annual summary
    w.writerow([])
    w.writerow(["Annual Summary", "Value"])
    w.writerow(["LCOE (RE) INR/kWh", f"{res['econ']['LCOE_RE_INR_per_kWh']:.2f}"])
    w.writerow(["System CoS INR/kWh", f"{res['econ']['cost_of_service_INR_per_kWh']:.2f}"])
    w.writerow(["CO2 avoided (t/yr)", f"{res['carbon']['co2_avoided_t']:.0f}"])
    w.writerow(["Carbon credit (INR)", f"{res['carbon']['carbon_credit_INR']:.0f}"])

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={_filename(res, run_id, 'csv')}"}
    )


@bp.get("/pdf/<run_id>")
def export_pdf(run_id):
    """Designed report (report.html + report.css). ?opt=<id> adds the ranked mixes
    from that /api/optimize run, if it was for the same place and load."""
    res = _cached_run(run_id)
    if res is None:
        return "Run not found or expired. Please evaluate again.", 404

    dfs = current_app.config["DATA"]
    row = dfs["islands"].loc[res["island"]]
    site = {"group": row.get("group"), "lat": float(row["lat_deg_N"]), "lon": float(row["lon_deg_E"]),
            "population": row.get("population_2011_approx"), "land_area": row.get("land_area_km2")}

    opt = current_app.config.get("OPT_CACHE", {}).get(request.args.get("opt", ""))
    ranked = None
    if opt and opt["island"] == res["island"] and abs(opt["load_kW"] - res["capacities"]["load_kW"]) < 1e-6:
        ranked = opt["feasible"]

    pdf = render_pdf(build_context(res, site, dfs["finance"], ranked))
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment;filename={_filename(res, run_id, 'pdf')}"}
    )
