"""
User Perspective - What the customer sees.
Simple language, composite score as a health indicator, and clear guidance.
"""

import streamlit as st
from data.engine_client import (
    get_available_vins, get_vehicle_detail, get_vehicle_explain, is_live,
)
from data.mock_data import VEHICLE_PROFILES


def _get_concise_reason(risk_factors: list) -> str:
    if not risk_factors:
        return "Temporary connectivity issue. Usually resolves on its own."
    if "heartbeat_stale" in risk_factors or "ecu_unresponsive" in risk_factors:
        return "Your vehicle hasn't communicated recently — likely in a low-signal area or sleep mode."
    if "tcu_flapping" in risk_factors:
        return "The vehicle's connection keeps dropping and reconnecting — usually due to poor network coverage."
    if "signal_weak" in risk_factors or "network_congestion" in risk_factors:
        return "Weak cellular signal at your vehicle's current location."
    if "battery_low" in risk_factors:
        return "Low vehicle battery is affecting the communication system."
    if "high_latency" in risk_factors:
        return "Network is slow in your area — commands may take longer."
    if "command_timeout_history" in risk_factors:
        return "Recent commands haven't been reaching the vehicle."
    if "device_twin_stale" in risk_factors:
        return "Vehicle data is outdated — waiting for a fresh update."
    return "Temporary connectivity issue. Usually resolves on its own."


def _get_tips(risk_factors: list) -> list:
    tips = []
    if "signal_weak" in risk_factors or "network_congestion" in risk_factors:
        tips.append("Move vehicle out of underground parking or signal dead zones")
    if "battery_low" in risk_factors:
        tips.append("Start the vehicle or plug in to charge")
    if "heartbeat_stale" in risk_factors or "tcu_flapping" in risk_factors or "ecu_unresponsive" in risk_factors:
        tips.append("Wait 15–30 min — the vehicle reconnects automatically")
    if "command_timeout_history" in risk_factors or "high_latency" in risk_factors:
        tips.append("Try again in a few minutes")
    if not tips:
        tips.append("Wait a few minutes — this usually resolves on its own")
    tips.append("Contact support if this persists over an hour")
    return tips


def _score_label(score: float) -> tuple:
    if score >= 85:
        return "Excellent", "#00D26A"
    if score >= 70:
        return "Good", "#4ECDC4"
    if score >= 50:
        return "Fair", "#FFB800"
    if score >= 30:
        return "Poor", "#FF8C00"
    return "Critical", "#FF4B4B"


def _hex_to_rgb(hex_color: str) -> list:
    hex_color = hex_color.lstrip("#")
    return [str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4)]


# --- Page starts ---

st.set_page_config(page_title="User Perspective", page_icon="👤", layout="wide")

st.markdown("""<style>
.status-box {border-radius:14px;padding:24px;margin:16px 0;}
.status-good {background:linear-gradient(135deg,#0a2a1a,#1a3a2a);border:1px solid #1a5a3a;}
.status-warn {background:linear-gradient(135deg,#2a2a0a,#3a3a1a);border:1px solid #5a5a1a;}
.status-bad {background:linear-gradient(135deg,#2a0a0a,#3a1a1a);border:1px solid #5a1a1a;}
.score-ring {width:100px;height:100px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto;font-size:1.8rem;font-weight:800;}
</style>""", unsafe_allow_html=True)

st.markdown("## 👤 User Perspective")
st.caption("What the customer sees — vehicle health in plain language")

vins = get_available_vins()
vin_display = {}
for vin in vins:
    profile = VEHICLE_PROFILES.get(vin, {})
    model = profile.get("model", "Vehicle")
    vin_display[vin] = f"{model} ({vin[-6:]})"

selected_vin = st.selectbox(
    "Select your vehicle",
    vins,
    format_func=lambda x: vin_display.get(x, x),
)

if not selected_vin:
    st.stop()

vehicle = get_vehicle_detail(selected_vin)

if "error" in vehicle:
    st.error("Vehicle not found.")
    st.stop()

profile = VEHICLE_PROFILES.get(selected_vin, {})
model = vehicle.get("model", profile.get("model", "Your Vehicle"))
status = vehicle.get("status", {})
if isinstance(status, dict):
    overall = status.get("overall", "unknown")
else:
    overall = status

scores = vehicle.get("scores", {})
composite = scores.get("composite_score", profile.get("composite", 0))
if isinstance(composite, float) and composite <= 1:
    composite = int(composite * 100)
composite = int(composite)

st.markdown(f"**{model}** · VIN: `{selected_vin}`")
st.markdown("---")

# --- Composite Score Display ---
label, color = _score_label(composite)

col_score, col_status = st.columns([1, 2.5])

with col_score:
    st.markdown(f"""
<div style="text-align:center;">
    <div class="score-ring" style="background:rgba({','.join(_hex_to_rgb(color))},0.12);border:3px solid {color};color:{color};">
        {composite}
    </div>
    <div style="color:{color};font-weight:700;margin-top:8px;">{label}</div>
    <div style="color:#8899A6;font-size:0.72rem;margin-top:2px;">Vehicle Health Score</div>
</div>
    """, unsafe_allow_html=True)

with col_status:
    if overall in ("healthy", "good", "low"):
        st.markdown("""<div class="status-box status-good">
            <div style="font-size:1.2rem;font-weight:700;color:#00D26A;">✅ All good — remote features are working</div>
            <div style="color:#8BC8A8;margin-top:6px;">Lock, unlock, climate, status check — everything is ready to use.</div>
        </div>""", unsafe_allow_html=True)

    elif overall in ("warning", "medium"):
        risk_factors = vehicle.get("risk_factors", [])
        why = _get_concise_reason(risk_factors)
        st.markdown(f"""<div class="status-box status-warn">
            <div style="font-size:1.2rem;font-weight:700;color:#FFB800;">⚠️ Remote features may be delayed</div>
            <div style="color:#C8B868;margin-top:6px;">{why}</div>
        </div>""", unsafe_allow_html=True)

    else:
        risk_factors = vehicle.get("risk_factors", [])
        why = _get_concise_reason(risk_factors)
        st.markdown(f"""<div class="status-box status-bad">
            <div style="font-size:1.2rem;font-weight:700;color:#FF4B4B;">🔴 Vehicle not reachable</div>
            <div style="color:#C88888;margin-top:6px;">{why}</div>
        </div>""", unsafe_allow_html=True)

# --- What to do (only if there's an issue) ---
if overall not in ("healthy", "good", "low"):
    risk_factors = vehicle.get("risk_factors", [])
    tips = _get_tips(risk_factors)

    st.markdown("")
    st.markdown("**What you can do:**")
    for tip in tips:
        st.markdown(f"→ {tip}")

    if overall not in ("warning", "medium"):
        st.markdown("")
        st.info("Commands you send will be **queued** and delivered once reconnected.")

# --- What does the score mean (collapsible) ---
st.markdown("---")
with st.expander("What does this score mean?"):
    st.markdown("""
Your **Vehicle Health Score** (0–100) tells you how reliably remote features will work right now. It combines:

| Factor | What it measures |
|--------|-----------------|
| **Reachability** | Can we reach your vehicle? (signal, heartbeat, connection stability) |
| **Command Success** | How likely is a command to go through? (based on recent history + current conditions) |
| **Data Freshness** | Is the vehicle's info up to date? |
| **Update Readiness** | Can software updates be installed? |

**Score ranges:**
- **85–100** — Everything works perfectly
- **70–84** — Working well, minor delays possible
- **50–69** — Some features may be slow or require retry
- **30–49** — Significant issues, commands will be queued
- **0–29** — Vehicle unreachable, needs reconnection or support
    """)

st.markdown("")
st.caption("Powered by Connected Experience Guardian")
