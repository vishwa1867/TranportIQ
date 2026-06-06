import os
import json
import csv
import io
from flask import Flask, render_template, request, jsonify, send_file
from agents import vehicle_agent, cost_agent, report_agent, _parse_weight

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs("uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# In-memory shipment history
shipment_history = []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/shipments", methods=["GET"])
def get_shipments():
    return jsonify(shipment_history)


@app.route("/api/process", methods=["POST"])
def process_shipment():
    try:
        # Accept JSON (manual form) or CSV upload
        if request.content_type and "multipart" in request.content_type:
            file = request.files.get("csv_file")
            if not file:
                return jsonify({"error": "No CSV file provided"}), 400
            stream = io.StringIO(file.stream.read().decode("utf-8"))
            reader = csv.DictReader(stream)
            rows = list(reader)
            if not rows:
                return jsonify({"error": "CSV is empty"}), 400
            row = rows[0]
            data = {
                "goods":       row.get("goods", ""),
                "weight_kg":   _parse_weight(row.get("weight_kg", "0")),
                "quantity":    row.get("quantity", ""),
                "origin":      row.get("origin", ""),
                "destination": row.get("destination", ""),
                "urgency":     row.get("urgency", "normal"),
                "notes":       row.get("notes", ""),
            }
        else:
            body = request.get_json()
            data = {
                "goods":       body.get("goods", ""),
                "weight_kg":   _parse_weight(str(body.get("weight_kg", "0"))),
                "quantity":    body.get("quantity", ""),
                "origin":      body.get("origin", ""),
                "destination": body.get("destination", ""),
                "urgency":     body.get("urgency", "normal"),
                "notes":       body.get("notes", ""),
            }

        # Run agents
        vehicle = vehicle_agent(data)
        cost    = cost_agent(data, vehicle)

        # Save PDF in reports folder
        import uuid, os
        from datetime import datetime
        shipment_id = f"SHP-{uuid.uuid4().hex[:8].upper()}"
        pdf_filename = f"reports/Shipment_{shipment_id}.pdf"

        # Patch report_agent to save to our path
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from datetime import timedelta
        from agents import _make_table

        today    = datetime.now()
        eta_date = today + timedelta(days=cost.get("eta_days", 2))
        doc      = SimpleDocTemplate(pdf_filename, pagesize=A4,
                      rightMargin=2*cm, leftMargin=2*cm,
                      topMargin=2*cm, bottomMargin=2*cm)
        styles   = getSampleStyleSheet()
        story    = []

        title_style   = ParagraphStyle("Title", parent=styles["Title"], fontSize=22,
                            textColor=colors.HexColor("#1a3c6e"), spaceAfter=4)
        sub_style     = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10,
                            textColor=colors.HexColor("#555555"), spaceAfter=2)
        section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=13,
                            textColor=colors.HexColor("#1a3c6e"), spaceBefore=14, spaceAfter=6)
        small         = ParagraphStyle("Small", parent=styles["Normal"], fontSize=9,
                            textColor=colors.HexColor("#444"))

        story.append(Paragraph("WHOLESALE TRANSPORT REPORT", title_style))
        story.append(Paragraph(f"Shipment ID: <b>{shipment_id}</b> &nbsp;|&nbsp; Date: {today.strftime('%d %B %Y')}", sub_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a3c6e")))
        story.append(Spacer(1, 10))

        for section, rows in [
            ("1. SHIPMENT DETAILS", [
                ["Field","Details"],["Goods",data["goods"]],["Weight",f"{data['weight_kg']:,} KG"],
                ["Quantity",data["quantity"]],["Origin",data["origin"]],["Destination",data["destination"]],
                ["Urgency",data["urgency"].capitalize()],["Notes",data["notes"] or "—"]]),
            ("2. RECOMMENDED VEHICLE", [
                ["Field","Details"],["Vehicle Type",vehicle["vehicle_type"]],
                ["Model",vehicle["vehicle_model"]],["Capacity",f"{vehicle['capacity_tons']} Tons"],
                ["Fuel",vehicle["fuel_type"]],["Avg Speed",f"{vehicle['avg_speed_kmph']} km/h"],
                ["Reason",vehicle["reason"]],["Loading Notes",vehicle["loading_notes"]]]),
        ]:
            story.append(Paragraph(section, section_style))
            story.append(_make_table(rows))
            story.append(Spacer(1, 8))

        cb = cost.get("cost_breakdown", {})
        story.append(Paragraph("3. COST ESTIMATE (INR)", section_style))
        story.append(_make_table([
            ["Component","Amount (INR)"],
            ["Base Freight",f"Rs {cb.get('base_freight',0):,}"],
            ["Fuel Surcharge",f"Rs {cb.get('fuel_surcharge',0):,}"],
            ["Toll Charges",f"Rs {cb.get('toll_charges',0):,}"],
            ["Loading/Unloading",f"Rs {cb.get('loading_unloading',0):,}"],
            ["Miscellaneous",f"Rs {cb.get('misc',0):,}"],
            ["TOTAL",f"Rs {cost['estimated_cost_inr']:,}"],
        ], highlight_last=True))
        story.append(Spacer(1, 8))

        story.append(Paragraph("4. ROUTE & ETA", section_style))
        story.append(_make_table([
            ["Field","Details"],
            ["Distance",f"~{cost['distance_km']:,} KM"],
            ["Route",cost["route_summary"]],
            ["Highway",cost["highway_used"]],
            ["ETA",f"~{cost['eta_days']} day(s) / {cost['eta_hours']} hrs"],
            ["Expected Delivery",eta_date.strftime("%d %B %Y")],
        ]))
        story.append(Spacer(1, 8))

        story.append(Paragraph("5. LOGISTICS TIPS", section_style))
        story.append(Paragraph(cost.get("tips","—"), styles["Normal"]))
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
        story.append(Paragraph(f"Generated {today.strftime('%d %b %Y %H:%M')} | Wholesale Transport Automation", small))
        doc.build(story)

        # Build history record
        record = {
            "id":          shipment_id,
            "date":        today.strftime("%d %b %Y %H:%M"),
            "goods":       data["goods"],
            "weight":      data["weight_kg"],
            "origin":      data["origin"],
            "destination": data["destination"],
            "urgency":     data["urgency"],
            "vehicle":     vehicle["vehicle_type"],
            "cost":        cost["estimated_cost_inr"],
            "eta_days":    cost["eta_days"],
            "pdf":         pdf_filename,
            "vehicle_detail": vehicle,
            "cost_detail":    cost,
        }
        shipment_history.insert(0, record)

        return jsonify({"success": True, "record": record})

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/download/<shipment_id>")
def download_pdf(shipment_id):
    for r in shipment_history:
        if r["id"] == shipment_id:
            return send_file(r["pdf"], as_attachment=True,
                             download_name=f"Shipment_{shipment_id}.pdf")
    return jsonify({"error": "Not found"}), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
