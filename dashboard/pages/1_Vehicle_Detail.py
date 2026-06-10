"""Vehicle Detail - Deep dive into a single vehicle with live engine data."""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from data.engine_client import (
    get_vehicle_detail, get_vehicle_explain, predict_command,
    get_available_vins, get_vehicle_history, is_live, COMMANDS,
)

st.set_page_config(page_title="Vehicle Detail", page_icon="🚗", layout="wide")


def prob_color_icon(pct):
    if pct > 75:
        return "🟢"
    if pct > 40:
        return "🟡"
    return "🔴"

st.markdown("""
<style>
    .vehicle-header {
        background: linear-gradient(135deg, #1B2028, #232D3B);
        border: 1px solid #2a3a4a;
        border-radius: 16px;
        padding: 24px;
        display: flex;
        align-items: center;
        gap: 24px;
    }
    .vin-large {
        font-size: 1.6rem;
        font-weight: 800;
        color: #E8E8E8;
        letter-spacing: 1px;
    }
    .gauge-container {
        background: linear-gradient(135deg, #1B2028, #1a2535);
        border: 1px solid #2a3a4a;
        border-radius: 14px;
        padding: 16px;
        text-align: center;
    }
    .detail-card {
        background: linear-gradient(135deg, #1B2028, #232D3B);
        border: 1px solid #2a3a4a;
        border-radius: 14px;
        padding: 20px;
    }
    .score-bar-track {
        background: #0a0f14;
        border-radius: 6px;
        height: 10px;
        overflow: hidden;
        margin-top: 4px;
    }
    .score-bar-fill {
        height: 100%;
        border-radius: 6px;
        transition: width 0.8s ease;
    }
</style>
""", unsafe_allow_html=True)

st.title("Vehicle Detail")

vins = get_available_vins()
selected_vin = st.selectbox("Select Vehicle", vins, key="vd_vin")

vehicle = get_vehicle_detail(selected_vin)
explanation = get_vehicle_explain(selected_vin)

if "error" in vehicle:
    st.error(f"Vehicle not found: {selected_vin}")
    st.stop()

# --- Vehicle Header ---
status_overall = vehicle.get("status", {}).get("overall", vehicle.get("status", "unknown")) if isinstance(vehicle.get("status"), dict) else vehicle.get("status", "unknown")
status_icons = {"healthy": "🟢", "good": "🟢", "low": "🟢", "warning": "🟡", "medium": "🟡", "critical": "🔴", "high": "🔴"}
status_colors = {"healthy": "#00D26A", "good": "#00D26A", "low": "#00D26A", "warning": "#FFB800", "medium": "#FFB800", "critical": "#FF4B4B", "high": "#FF4B4B"}

icon = status_icons.get(status_overall, "⚪")
color = status_colors.get(status_overall, "#888")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown(f"### {icon} {vehicle.get('vin', selected_vin)}")
    st.caption(f"{vehicle.get('model', 'Unknown')} | {vehicle.get('region', 'Unknown')}")
with col2:
    st.markdown(f"**Status:** {status_overall.title()}")
    updated = vehicle.get("updated_at", "N/A")
    if isinstance(updated, str) and len(updated) > 19:
        updated = updated[:19]
    st.caption(f"Updated: {updated}")
with col3:
    risk_factors = vehicle.get("risk_factors", [])
    st.markdown(f"**Risk Factors:** {len(risk_factors)}")
    if risk_factors:
        st.caption(f"Top: `{risk_factors[0]}`")

st.divider()

# --- Customer Message ---
if isinstance(explanation, dict):
    severity = explanation.get("severity", "info")
    customer_msg = explanation.get("customer_message", "")
    tech_details = explanation.get("technical_details", "")
else:
    severity = "info"
    customer_msg = ""
    tech_details = ""

sev_icons = {"good": "🟢", "info": "🔵", "warning": "🟡", "critical": "🔴"}
st.markdown(f"{sev_icons.get(severity, '⚪')} **Customer Message:** *{customer_msg}*")

if tech_details:
    with st.expander("Technical Details"):
        st.code(tech_details)
        if risk_factors:
            st.markdown("**Risk Factors:** " + ", ".join(f"`{rf}`" for rf in risk_factors))

st.divider()

# --- Score Gauges ---
st.subheader("Experience Scores")
scores = vehicle.get("scores", {})

score_items = [
    ("Composite", scores.get("composite_score", 0)),
    ("Reachability", scores.get("reachability_score", scores.get("connectivity_score", 0))),
    ("Cmd Probability", scores.get("command_probability", 0)),
    ("OTA Readiness", scores.get("ota_readiness_score", scores.get("command_history_score", 0))),
    ("Data Freshness", scores.get("data_freshness_score", scores.get("vehicle_health_score", 0))),
]

score_cols = st.columns(5)

for col, (label, value) in zip(score_cols, score_items):
    with col:
        if isinstance(value, float) and value <= 1:
            display_val = int(value * 100)
        else:
            display_val = int(value) if isinstance(value, (int, float)) else 0

        bar_color = "#00D26A" if display_val > 70 else "#FFB800" if display_val > 45 else "#FF4B4B"

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=display_val,
            title={"text": label, "font": {"size": 12, "color": "#8899A6"}},
            number={"font": {"size": 28, "color": bar_color}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "#1B2028"},
                "bar": {"color": bar_color, "thickness": 0.7},
                "bgcolor": "#1B2028",
                "bordercolor": "#2a3a4a",
                "borderwidth": 1,
                "steps": [
                    {"range": [0, 35], "color": "rgba(255,75,75,0.08)"},
                    {"range": [35, 70], "color": "rgba(255,184,0,0.06)"},
                    {"range": [70, 100], "color": "rgba(0,210,106,0.06)"},
                ],
                "threshold": {"line": {"color": "#4ECDC4", "width": 2}, "thickness": 0.8, "value": display_val},
            },
        ))
        fig.update_layout(
            height=160,
            margin=dict(t=40, b=0, l=15, r=15),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#FAFAFA",
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Command Predictions ---
st.subheader("Command Predictions")
st.caption("Predicted success probability for each command type")

predictions = []
for cmd in COMMANDS:
    pred = predict_command(selected_vin, cmd)
    p = pred.get("prediction", {})
    a = pred.get("recommended_action", {})
    prob = p.get("success_probability", 0)
    prob_pct = prob * 100 if isinstance(prob, (int, float)) and prob <= 1 else (prob if isinstance(prob, (int, float)) else 0)

    predictions.append({
        "Command": cmd.replace("_", " ").title(),
        "Success %": int(prob_pct),
        "Risk Level": p.get("risk_level", "unknown"),
        "Will Fail": "Yes" if p.get("will_likely_fail", False) else "No",
        "Action": a.get("display_label", "Unknown"),
        "Wait (min)": a.get("estimated_wait_minutes", 0) or 0,
        "Latency (ms)": p.get("estimated_latency_ms", None),
    })

pred_df = pd.DataFrame(predictions)

col_chart, col_table = st.columns([1.5, 1])

with col_chart:
    colors = ["#00D26A" if v > 75 else "#FFB800" if v > 40 else "#FF4B4B" for v in pred_df["Success %"]]
    fig_pred = go.Figure()
    fig_pred.add_trace(go.Bar(
        x=pred_df["Command"], y=pred_df["Success %"],
        marker_color=colors,
        text=[f"{v}%" for v in pred_df["Success %"]],
        textposition="outside",
    ))
    fig_pred.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
        yaxis_range=[0, 110], xaxis_title="", yaxis_title="Success %",
        margin=dict(l=40, r=20, t=20, b=60), height=300,
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    fig_pred.add_hline(y=75, line_dash="dot", line_color="rgba(0,210,106,0.3)")
    fig_pred.add_hline(y=40, line_dash="dot", line_color="rgba(255,75,75,0.3)")
    st.plotly_chart(fig_pred, use_container_width=True)

with col_table:
    st.dataframe(pred_df, use_container_width=True, hide_index=True, height=300)

st.divider()

# --- Interactive Predict ---
st.subheader("Try a Prediction")
col_cmd, col_btn = st.columns([3, 1])
with col_cmd:
    test_command = st.selectbox("Command", COMMANDS, format_func=lambda x: x.replace("_", " ").title(), key="test_cmd")
with col_btn:
    st.markdown("")
    st.markdown("")
    run_pred = st.button("⚡ Predict", type="primary")

if run_pred:
    result = predict_command(selected_vin, test_command)
    pred = result.get("prediction", {})
    action = result.get("recommended_action", {})
    expl = result.get("explanation", {})

    prob = pred.get("success_probability", 0)
    prob_pct = int(prob * 100) if isinstance(prob, (int, float)) and prob <= 1 else int(prob or 0)
    prob_color = "#00D26A" if prob_pct > 75 else "#FFB800" if prob_pct > 40 else "#FF4B4B"

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown(f"### {prob_color_icon(prob_pct)} {prob_pct}% Success Probability")
        st.markdown(f"**Risk Level:** {pred.get('risk_level', 'N/A')}")
        st.markdown(f"**Will Fail:** {'Yes' if pred.get('will_likely_fail') else 'No'}")
        if pred.get("estimated_latency_ms"):
            st.markdown(f"**Est. Latency:** {pred['estimated_latency_ms']}ms")
        rf = pred.get("risk_factors", [])
        if rf:
            st.markdown("**Risk Factors:** " + ", ".join(f"`{r}`" for r in rf))

    with col_r2:
        st.markdown(f"### Recommended: {action.get('display_label', 'N/A')}")
        st.markdown(f"**Reason:** {action.get('reason', 'N/A')}")
        wait = action.get("estimated_wait_minutes")
        if wait:
            st.markdown(f"**Est. Wait:** {wait} minutes")
        fb = action.get("fallback_action")
        if fb:
            st.markdown(f"**Fallback:** {str(fb).replace('_', ' ').title()}")

    if expl.get("customer_message"):
        st.info(f"💬 {expl['customer_message']}")
    if expl.get("technical_details"):
        with st.expander("Technical Details"):
            st.code(expl["technical_details"])

# --- Score History ---
st.divider()
st.subheader("Score History")

history = get_vehicle_history(selected_vin)
if history and history.get("history"):
    hist_df = pd.DataFrame(history["history"])
    fig_h = go.Figure()
    fig_h.add_trace(go.Scatter(
        x=list(range(len(hist_df))), y=hist_df["composite_score"],
        mode="lines+markers", name="Composite",
        line=dict(color="#4ECDC4", width=3), fill="tozeroy", fillcolor="rgba(78,205,196,0.08)",
    ))
    fig_h.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
        height=220, margin=dict(l=40, r=20, t=10, b=30),
        yaxis_range=[0, 100], yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(fig_h, use_container_width=True)
else:
    st.caption("Score history available when Guardian Engine is running with simulator.")

# --- Raw Payload (if available from engine) ---
raw = vehicle.get("raw_payload")
if raw and isinstance(raw, dict) and "vin" in raw:
    with st.expander("Raw Vehicle Payload"):
        st.json(raw)
