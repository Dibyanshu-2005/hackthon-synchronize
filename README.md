# Predictive Connected Experience Guardian

## What is this?

A dashboard that predicts if your car's remote commands (lock, unlock, climate, etc.) will work BEFORE you press the button. If they won't work, it tells you why and what to do instead.

---

## How to Run (Simple Version)

### Step 1: Download the code

```
git clone https://github.com/Dibyanshu-2005/hackthon-synchronize.git
cd hackthon-synchronize
```

### Step 2: Install Python stuff

```
cd Heckaton
pip install -r requirements.txt
```

### Step 3: Run the dashboard

```
streamlit run app.py
```

A browser tab will open at **http://localhost:8501** — that's your dashboard!

---

## Want the full experience? (Optional)

This connects the dashboard to the real prediction engine for live data.

### Terminal 1 — Start the engine:

```
cd Guardian_Engine
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Terminal 2 — Start the dashboard:

```
cd Heckaton
streamlit run app.py
```

When the engine is running, the dashboard shows a green "ENGINE LIVE" badge. Without it, you'll see "DEMO MODE" with sample data — both work fine for the demo.

---

## Pages in the Dashboard

| Page | What it shows |
|------|--------------|
| Fleet Overview | All vehicles at a glance, health scores, risk map |
| Vehicle Detail | Deep dive into one vehicle's scores and predictions |
| Command Analytics | Success rates, latency, failure patterns |
| OTA Status | Which vehicles are ready for software updates |
| Alerts & Actions | Active issues and what to do about them |
| Business Insights | Executive view — impact numbers, heatmaps |
| Guardian Intelligence | **THE COOL ONE** — predict commands live, what-if simulator |
| Live Monitor | Real-time tracking with auto-refresh |

---

## Troubleshooting

**"streamlit not found"** — Run `pip install streamlit` first

**"No module named data"** — Make sure you're inside the `Heckaton` folder when you run `streamlit run app.py`

**Dashboard shows "DEMO MODE"** — That's fine! It means the engine isn't running. The dashboard still works with sample data.

---

## Team

Built at Hackathon 2026
