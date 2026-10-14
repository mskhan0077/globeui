"""CSV and PDF Export routes."""
import io
import csv
from flask import Blueprint, Response, current_app, send_file
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

bp = Blueprint("export", __name__)

@bp.get("/csv/<run_id>")
def export_csv(run_id):
    cache = current_app.config.get("CACHE", {})
    if run_id not in cache:
        return "Run not found or expired. Please evaluate again.", 404

    res = cache[run_id]
    buf = io.StringIO()
    w = csv.writer(buf)
    
    # Write Monthly Table
    w.writerow(["Month", "Hours", "Wind_kWh", "FPV_kWh", "OTEC_kWh",
                "Total_kWh", "Load_kWh", "Delivered_kWh", "Unmet_kWh", "Coverage"])
    for row in res["monthly"]:
        w.writerow([
            row["month_num"], row["hours"], row["gen_wind_kWh"], row["gen_fpv_kWh"],
            row["gen_otec_kWh"], row["gen_total_kWh"], row["load_kWh"],
            row["delivered_kWh"], row["unmet_kWh"], row["coverage"]
        ])
    
    # Write Annual Summary
    w.writerow([])
    w.writerow(["Annual Summary", "Value"])
    w.writerow(["LCOE (RE) INR/kWh", f"{res['econ']['LCOE_RE_INR_per_kWh']:.2f}"])
    w.writerow(["System CoS INR/kWh", f"{res['econ']['cost_of_service_INR_per_kWh']:.2f}"])
    w.writerow(["CO2 avoided (t/yr)", f"{res['carbon']['co2_avoided_t']:.0f}"])
    w.writerow(["Carbon credit (INR)", f"{res['carbon']['carbon_credit_INR']:.0f}"])

    return Response(
        buf.getvalue(), 
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=bluegrid_{res['island'].lower()}_{run_id[:6]}.csv"}
    )

@bp.get("/pdf/<run_id>")
def export_pdf(run_id):
    cache = current_app.config.get("CACHE", {})
    if run_id not in cache:
        return "Run not found or expired. Please evaluate again.", 404
        
    res = cache[run_id]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    
    story = [Paragraph(f"BlueGrid Executive Summary — {res['island']}", styles["Title"])]
    story.append(Paragraph(f"Target load: {res['capacities']['load_kW']} kW", styles["Normal"]))
    story.append(Spacer(1, 12))
    
    # Define Table Data
    lpsp = res['reliability'].get('lpsp_hourly', res['reliability']['lpsp_monthly'])
    rows = [
        ["Metric", "Value"],
        ["LCOE (RE) INR/kWh", f"Rs. {res['econ']['LCOE_RE_INR_per_kWh']:.2f}"],
        ["System Cost of Service INR/kWh", f"Rs. {res['econ']['cost_of_service_INR_per_kWh']:.2f}"],
        ["Plant Load Factor (PLF)", f"{res['plf_target']*100:.1f}%"],
        ["Loss of Power Supply (LPSP)", f"{lpsp*100:.2f}%"],
        ["CO2 Avoided", f"{res['carbon']['co2_avoided_t']:.0f} tonnes/yr"],
        ["CAPEX (Island-Adjusted)", f"Rs. {res['econ']['capex_INR']/1e7:.2f} Cr"]
    ]
    
    story.append(Table(rows, colWidths=[200, 150]))
    doc.build(story)
    
    buf.seek(0)
    return send_file(
        buf, 
        as_attachment=True, 
        download_name=f"bluegrid_{res['island'].lower()}_{run_id[:6]}.pdf", 
        mimetype="application/pdf"
    )