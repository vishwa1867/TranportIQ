import os
import re
import json
import csv
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from groq import Groq
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

# ─────────────────────────────────────────────────────────
# HELPER: Call Groq LLM
# ─────────────────────────────────────────────────────────
def call_llm(system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0.4,
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────────────────
# HELPER: Safely parse weight — strips symbols like ' " kg etc.
# ─────────────────────────────────────────────────────────
def _parse_weight(raw: str) -> float:
    cleaned = re.sub(r"[^\d.]", "", raw.strip())
    if not cleaned:
        raise ValueError(f"Could not read weight '{raw}'. Please enter a number like 5000")
    return float(cleaned)


# ─────────────────────────────────────────────────────────
# AGENT 1 — INPUT AGENT
# Parses typed input or reads from CSV
# ─────────────────────────────────────────────────────────
def input_agent(mode: str) -> dict:
    print("\n" + "="*55)
    print("📥  AGENT 1 — INPUT AGENT")
    print("="*55)

    if mode == "csv":
        csv_path = input("Enter path to your CSV file (or press Enter for sample_input.csv): ").strip()
        if not csv_path:
            csv_path = "sample_input.csv"
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            raise ValueError("CSV file is empty.")
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
        print("\nPlease enter shipment details:\n")
        print("  (Tip: for weight just type numbers, e.g. 5000)\n")

        goods = ""
        while not goods:
            goods = input("  Goods/Product name       : ").strip()

        weight_kg = None
        while weight_kg is None:
            raw = input("  Total weight (in KG)     : ").strip()
            try:
                weight_kg = _parse_weight(raw)
            except ValueError:
                print("  ⚠️  Please enter a valid number, e.g. 5000")

        quantity = input("  Quantity (e.g. 200 bags)  : ").strip()
        origin   = input("  Origin city               : ").strip()
        destination = input("  Destination city          : ").strip()
        urgency  = input("  Urgency (normal/urgent)   : ").strip() or "normal"
        notes    = input("  Special notes (optional)  : ").strip()

        data = {
            "goods":       goods,
            "weight_kg":   weight_kg,
            "quantity":    quantity,
            "origin":      origin,
            "destination": destination,
            "urgency":     urgency,
            "notes":       notes,
        }

    print(f"\n  ✅ Input captured: {data['goods']} | {data['weight_kg']} KG | {data['origin']} → {data['destination']}")
    return data


# ─────────────────────────────────────────────────────────
# AGENT 2 — VEHICLE RESEARCH AGENT
# ─────────────────────────────────────────────────────────
def vehicle_agent(data: dict) -> dict:
    print("\n" + "="*55)
    print("🔍  AGENT 2 — VEHICLE RESEARCH AGENT")
    print("="*55)

    system = """You are an expert Indian logistics and freight consultant.
Given shipment details, recommend the MOST ECONOMICAL vehicle for Pan-India transport.
Respond ONLY with valid JSON — no extra text, no markdown fences.
JSON format:
{
  "vehicle_type": "...",
  "vehicle_model": "...",
  "capacity_tons": ...,
  "reason": "...",
  "fuel_type": "...",
  "avg_speed_kmph": ...,
  "loading_notes": "..."
}"""

    user = f"""Shipment details:
- Goods: {data['goods']}
- Weight: {data['weight_kg']} KG
- Quantity: {data['quantity']}
- Route: {data['origin']} to {data['destination']}
- Urgency: {data['urgency']}
- Notes: {data['notes']}

Recommend the best economical vehicle."""

    raw = call_llm(system, user)
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    vehicle = json.loads(clean)
    print(f"  ✅ Recommended: {vehicle['vehicle_type']} — {vehicle['vehicle_model']}")
    return vehicle


# ─────────────────────────────────────────────────────────
# AGENT 3 — COST & ETA AGENT
# ─────────────────────────────────────────────────────────
def cost_agent(data: dict, vehicle: dict) -> dict:
    print("\n" + "="*55)
    print("💰  AGENT 3 — COST & ETA AGENT")
    print("="*55)

    system = """You are an Indian freight cost estimator with deep knowledge of road transport rates.
Given shipment and vehicle info, estimate realistic costs and ETA for Pan-India delivery.
Respond ONLY with valid JSON — no extra text, no markdown fences.
JSON format:
{
  "distance_km": ...,
  "estimated_cost_inr": ...,
  "cost_breakdown": {
    "base_freight": ...,
    "fuel_surcharge": ...,
    "toll_charges": ...,
    "loading_unloading": ...,
    "misc": ...
  },
  "eta_hours": ...,
  "eta_days": ...,
  "route_summary": "...",
  "highway_used": "...",
  "tips": "..."
}"""

    user = f"""Shipment:
- Goods: {data['goods']}
- Weight: {data['weight_kg']} KG
- Route: {data['origin']} to {data['destination']}
- Urgency: {data['urgency']}

Vehicle:
- Type: {vehicle['vehicle_type']}
- Model: {vehicle['vehicle_model']}
- Avg Speed: {vehicle['avg_speed_kmph']} km/h
- Fuel: {vehicle['fuel_type']}

Estimate total cost (INR) and ETA."""

    raw = call_llm(system, user)
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    cost = json.loads(clean)
    print(f"  ✅ Estimated cost: ₹{cost['estimated_cost_inr']:,} | ETA: {cost['eta_days']} day(s)")
    return cost


# ─────────────────────────────────────────────────────────
# AGENT 4 — PDF REPORT AGENT
# ─────────────────────────────────────────────────────────
def report_agent(data: dict, vehicle: dict, cost: dict) -> str:
    print("\n" + "="*55)
    print("📄  AGENT 4 — PDF REPORT AGENT")
    print("="*55)

    shipment_id = f"SHP-{uuid.uuid4().hex[:8].upper()}"
    today = datetime.now()
    eta_date = today + timedelta(days=cost.get("eta_days", 2))
    filename = f"Shipment_{shipment_id}.pdf"

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    story  = []

    title_style = ParagraphStyle("Title", parent=styles["Title"],
        fontSize=22, textColor=colors.HexColor("#1a3c6e"), spaceAfter=4)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#555555"), spaceAfter=2)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"],
        fontSize=13, textColor=colors.HexColor("#1a3c6e"),
        spaceBefore=14, spaceAfter=6)
    normal = styles["Normal"]
    small  = ParagraphStyle("Small", parent=normal, fontSize=9, textColor=colors.HexColor("#444"))

    story.append(Paragraph("WHOLESALE TRANSPORT REPORT", title_style))
    story.append(Paragraph(f"Shipment ID: <b>{shipment_id}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Date: {today.strftime('%d %B %Y')}", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a3c6e")))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. SHIPMENT DETAILS", section_style))
    ship_data = [
        ["Field", "Details"],
        ["Goods / Product", data["goods"]],
        ["Total Weight", f"{data['weight_kg']:,} KG"],
        ["Quantity", data["quantity"]],
        ["Origin", data["origin"]],
        ["Destination", data["destination"]],
        ["Urgency", data["urgency"].capitalize()],
        ["Special Notes", data["notes"] or "—"],
    ]
    story.append(_make_table(ship_data))
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. RECOMMENDED VEHICLE", section_style))
    veh_data = [
        ["Field", "Details"],
        ["Vehicle Type", vehicle["vehicle_type"]],
        ["Model / Category", vehicle["vehicle_model"]],
        ["Capacity", f"{vehicle['capacity_tons']} Tons"],
        ["Fuel Type", vehicle["fuel_type"]],
        ["Avg Speed", f"{vehicle['avg_speed_kmph']} km/h"],
        ["Why Chosen", vehicle["reason"]],
        ["Loading Notes", vehicle["loading_notes"]],
    ]
    story.append(_make_table(veh_data))
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. COST ESTIMATE (INR)", section_style))
    cb = cost.get("cost_breakdown", {})
    cost_data = [
        ["Component", "Amount (INR)"],
        ["Base Freight", f"Rs {cb.get('base_freight', 0):,}"],
        ["Fuel Surcharge", f"Rs {cb.get('fuel_surcharge', 0):,}"],
        ["Toll Charges", f"Rs {cb.get('toll_charges', 0):,}"],
        ["Loading / Unloading", f"Rs {cb.get('loading_unloading', 0):,}"],
        ["Miscellaneous", f"Rs {cb.get('misc', 0):,}"],
        ["TOTAL ESTIMATED COST", f"Rs {cost['estimated_cost_inr']:,}"],
    ]
    story.append(_make_table(cost_data, highlight_last=True))
    story.append(Spacer(1, 8))

    story.append(Paragraph("4. ROUTE & DELIVERY ETA", section_style))
    route_data = [
        ["Field", "Details"],
        ["Distance", f"~{cost['distance_km']:,} KM"],
        ["Route Summary", cost["route_summary"]],
        ["Highway / Road", cost["highway_used"]],
        ["ETA (Hours)", f"~{cost['eta_hours']} hours"],
        ["ETA (Days)", f"~{cost['eta_days']} day(s)"],
        ["Expected Delivery", eta_date.strftime("%d %B %Y")],
    ]
    story.append(_make_table(route_data))
    story.append(Spacer(1, 8))

    story.append(Paragraph("5. LOGISTICS TIPS", section_style))
    story.append(Paragraph(cost.get("tips", "No additional tips."), normal))
    story.append(Spacer(1, 16))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Generated on {today.strftime('%d %b %Y %H:%M')} | Powered by Wholesale Transport Automation",
        small
    ))

    doc.build(story)
    print(f"  ✅ PDF saved: {filename}")
    return filename


def _make_table(data: list, highlight_last: bool = False) -> Table:
    col_widths = [6*cm, 11*cm]
    t = Table(data, colWidths=col_widths)
    style = [
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#1a3c6e")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 10),
        ("ALIGN",       (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME",    (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4fb"), colors.white]),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]
    if highlight_last:
        style += [
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#1a3c6e")),
            ("TEXTCOLOR",  (0, -1), (-1, -1), colors.white),
            ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


# ─────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────
def main():
    print("\n" + "="*55)
    print("  WHOLESALE TRANSPORT AUTOMATION SYSTEM")
    print("="*55)
    print("\nHow would you like to enter shipment details?")
    print("  1. Type manually")
    print("  2. Load from CSV file")
    choice = input("\nEnter 1 or 2: ").strip()
    mode = "csv" if choice == "2" else "manual"

    data    = input_agent(mode)
    vehicle = vehicle_agent(data)
    cost    = cost_agent(data, vehicle)
    pdf     = report_agent(data, vehicle, cost)

    print("\n" + "="*55)
    print(f"  ALL DONE! Report saved as: {pdf}")
    print("="*55 + "\n")


if __name__ == "__main__":
    main()
