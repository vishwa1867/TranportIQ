# 🚛 Wholesale Transport Automation System

A multi-agent AI app that takes your shipment details and automatically:
- Recommends the most **economical vehicle** for your goods
- Estimates **cost & ETA** for Pan-India delivery
- Generates a **professional PDF report** with full shipment details

Powered by **Groq (free)** + LLaMA 3.3 70B

---

## 🤖 How the Agents Work

```
You enter shipment details
        ↓
📥 INPUT AGENT        — reads your input (typed or CSV)
        ↓
🔍 VEHICLE AGENT      — recommends best economical vehicle
        ↓
💰 COST & ETA AGENT   — estimates cost breakdown + delivery time
        ↓
📄 PDF REPORT AGENT   — generates professional shipment report PDF
```

---

## 🚀 Step-by-Step Setup

### Step 1 — Get your FREE Groq API Key
1. Go to 👉 https://console.groq.com
2. Sign up (free, no credit card needed)
3. Click **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

---

### Step 2 — Set up your project folder

Create a folder anywhere on your computer, e.g.:
```
C:\Users\YourName\transport_automation\
```

Place these files inside:
```
transport_automation/
├── agents.py
├── requirements.txt
├── .env.example
├── sample_input.csv
└── README.md
```

---

### Step 3 — Create your .env file

1. Rename `.env.example` → `.env`
2. Open `.env` and paste your Groq key:
```
GROQ_API_KEY=gsk_your_actual_key_here
```
> ⚠️ Never share this file or upload it to GitHub!

---

### Step 4 — Install dependencies

Open terminal / Anaconda Prompt in your project folder:
```bash
pip install -r requirements.txt
```

---

### Step 5 — Run the app

```bash
python agents.py
```

You'll see:
```
🚛  WHOLESALE TRANSPORT AUTOMATION SYSTEM

How would you like to enter shipment details?
  1. Type manually
  2. Load from CSV file

Enter 1 or 2:
```

---

## 📋 Input Options

### Option 1: Type manually
Enter details one by one when prompted:
```
Goods/Product name       : Rice (Basmati)
Total weight (in KG)     : 5000
Quantity (e.g. 200 bags) : 100 bags
Origin city              : Delhi
Destination city         : Mumbai
Urgency (normal/urgent)  : normal
Special notes (optional) : Food grade, handle with care
```

### Option 2: Load from CSV
Use the provided `sample_input.csv` or create your own with these columns:
```
goods, weight_kg, quantity, origin, destination, urgency, notes
```

---

## 📄 Output PDF Includes

| Section | Details |
|---------|---------|
| Shipment Details | Goods, weight, quantity, route |
| Recommended Vehicle | Type, model, capacity, fuel type |
| Cost Estimate | Base freight, toll, fuel surcharge, total |
| Route & ETA | Distance, highway, expected delivery date |
| Logistics Tips | AI-generated tips for your shipment |

The PDF is saved in the same folder as `agents.py` with a unique shipment ID.
Example: `Shipment_SHP-A1B2C3D4.pdf`

---

## 💡 Example Shipments to Try

| Goods | Weight | Route |
|-------|--------|-------|
| Rice Bags | 5000 KG | Delhi → Mumbai |
| Electronics | 800 KG | Bangalore → Kolkata |
| Cement | 20000 KG | Hyderabad → Chennai |
| Cotton Bales | 3000 KG | Surat → Ludhiana |

---

## ❓ Troubleshooting

| Problem | Fix |
|---------|-----|
| `GROQ_API_KEY not found` | Check your `.env` file exists and has the key |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again |
| `JSON decode error` | Run again — occasional LLM formatting glitch |
| CSV not found | Make sure `sample_input.csv` is in same folder |
