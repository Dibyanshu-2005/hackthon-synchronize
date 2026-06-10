# Predictive Connected Experience Guardian

A proactive intelligence layer for connected vehicles. Predicts if remote commands (lock, unlock, climate, etc.) will succeed BEFORE sending — and tells you why and what to do if they won't.

---

## Quick Start

### Step 1: Clone

```
git clone https://github.com/Dibyanshu-2005/hackthon-synchronize.git
cd hackthon-synchronize
```

### Step 2: Install

```
cd dashboard
pip install -r requirements.txt
```

### Step 3: Run

```
streamlit run app.py
```

Opens at **http://localhost:8501**

---

## Full Live Mode (Engine + Simulator + Dashboard)

Three terminals:

```bash
# Terminal 1 — Simulator (generates live vehicle telemetry)
cd guardian_engine/Simulator
./simulator.exe -output websocket

# Terminal 2 — Guardian Engine (scores, predicts, explains)
cd guardian_engine
pip install -r requirements.txt
uvicorn main:app --port 8000

# Terminal 3 — Dashboard
cd dashboard
streamlit run app.py
```

When the engine is running, the dashboard shows **"ENGINE LIVE"**. Without it, you get **"DEMO MODE"** with realistic sample data.

Toggle **"Live Refresh"** in the sidebar for auto-updating data.

---

## Dashboard Pages

| Page | Purpose |
|------|---------|
| Fleet Overview | All vehicles at a glance — who needs attention |
| User Perspective | Customer-facing view — health score, plain-language status |
| Vehicle Detail | Deep dive into one vehicle's scores and predictions |
| Guardian Intelligence | Live predictions, command execution, what-if simulator |
| Command Analytics | Historical success rates, latency, failure patterns |
| Alerts & Actions | Active issues with recommended actions |

---

## Project Structure

```
├── dashboard/                  # Streamlit frontend
│   ├── app.py                  # Main page (Fleet Overview)
│   ├── pages/                  # Dashboard pages
│   ├── data/
│   │   ├── engine_client.py    # API client (connects to guardian_engine)
│   │   └── mock_data.py        # Fallback demo data
│   └── requirements.txt
│
├── guardian_engine/            # FastAPI backend
│   ├── main.py                # API server + simulator bridge
│   ├── scoring.py             # Multi-factor scoring model
│   ├── predictor.py           # Per-command success prediction
│   ├── explainer.py           # Customer-friendly message generation
│   ├── actions.py             # Action recommendation engine
│   ├── models.py              # Core data models
│   ├── payload_adapter.py     # Raw telemetry → VehicleState
│   ├── api_models.py          # Pydantic API schemas
│   ├── Simulator/             # Go simulator (5 vehicles, live telemetry)
│   └── requirements.txt
│
└── README.md
```

---

## Troubleshooting

**"streamlit not found"** — Run `pip install streamlit`

**"No module named data"** — Make sure you're inside the `dashboard/` folder

**"DEMO MODE"** — Engine isn't running. Dashboard works fine with sample data.

---

## Team

Built at Hackathon 2026 — Predictive Connected Experience Guardian
