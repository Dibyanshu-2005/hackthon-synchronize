"""OTA Status - Over-the-air update readiness derived from Guardian Engine predictions."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data.engine_client import predict_command, get_available_vins, get_vehicles, is_live

st.set_page_config(page_title="OTA Status", page_icon="📡", layout="wide")

st.markdown("""
<style>
    .ota-header {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #9B59B6 0%, #3498DB 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="ota-header">OTA Update Status</p>', unsafe_allow_html=True)
st.caption(f"{'🟢 Live Engine' if is_live() else '🟡 Demo Mode'} | OTA readiness from vehicle health + ota_install predictions")

vins = get_available_vins()
vehicles_resp = get_vehicles()
vehicles_list = vehicles_resp.get("vehicles", [])
vehicles_map = {v.get("vin"): v for v in vehicles_list}

ota_predictions = []
for vin in vins:
    pred = predict_command(vin, "ota_install")
    p = pred.get("prediction", {})
    s = pred.get("scores", {})
    e = pred.get("explanation", {})
    a = pred.get("recommended_action", {})
    v_info = vehicles_map.get(vin, {})

    prob = p.get("success_probability", 0)
    prob_pct = prob * 100 if isinstance(prob, (int, float)) and prob <= 1 else (prob if isinstance(prob, (int, float)) else 0)

    ota_predictions.append({
        "vin": vin,
        "model": v_info.get("model", "Unknown"),
        "success_probability": prob_pct / 100,
        "success_pct": round(prob_pct, 1),
        "risk_level": p.get("risk_level", "unknown"),
        "will_fail": p.get("will_likely_fail", False),
        "risk_factors": p.get("risk_factors", []),
        "severity": e.get("severity", "info"),
        "customer_message": e.get("customer_message", ""),
        "technical_details": e.get("technical_details", ""),
        "recommended_action": a.get("display_label", "Unknown"),
        "action_reason": a.get("reason", ""),
        "estimated_wait": a.get("estimated_wait_minutes", 0) or 0,
        "composite_score": s.get("composite_score", 0),
        "reachability_score": s.get("reachability_score", s.get("connectivity_score", 0)),
    })

ota_df = pd.DataFrame(ota_predictions)

# --- Summary Metrics ---
col1, col2, col3, col4 = st.columns(4)

ready = len(ota_df[ota_df["success_probability"] > 0.75])
risky = len(ota_df[(ota_df["success_probability"] > 0.4) & (ota_df["success_probability"] <= 0.75)])
blocked = len(ota_df[ota_df["success_probability"] <= 0.4])
will_fail_count = len(ota_df[ota_df["will_fail"]])

summary = [
    ("OTA Ready", str(ready), "#00D26A"),
    ("Risky", str(risky), "#FFB800"),
    ("Blocked", str(blocked), "#FF4B4B"),
    ("Will Fail", str(will_fail_count), "#9B59B6"),
]

for col, (label, value, color) in zip([col1, col2, col3, col4], summary):
    with col:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1B2028,#232D3B);border:1px solid #2a3a4a;border-radius:14px;padding:18px;text-align:center;border-top:3px solid {color};">
            <div style="font-size:2rem;font-weight:800;color:{color};">{value}</div>
            <div style="font-size:0.72rem;color:#8899A6;text-transform:uppercase;letter-spacing:1px;">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# --- OTA Success Chart ---
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("OTA Success Probability by Vehicle")
    ota_sorted = ota_df.sort_values("success_pct")
    colors = ["#00D26A" if v > 75 else "#FFB800" if v > 40 else "#FF4B4B" for v in ota_sorted["success_pct"]]
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=ota_sorted["vin"], y=ota_sorted["success_pct"],
        marker_color=colors,
        text=[f"{v:.0f}%" for v in ota_sorted["success_pct"]],
        textposition="outside",
    ))
    fig_bar.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
        yaxis_range=[0, 110], yaxis_title="Success %", xaxis_title="",
        margin=dict(l=40, r=20, t=20, b=40), height=320,
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    fig_bar.add_hline(y=75, line_dash="dot", line_color="rgba(0,210,106,0.3)", annotation_text="Ready")
    fig_bar.add_hline(y=40, line_dash="dot", line_color="rgba(255,75,75,0.3)", annotation_text="Blocked")
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.subheader("Composite vs Reachability")
    fig_scatter = px.scatter(
        ota_df, x="reachability_score", y="composite_score",
        color="severity", hover_name="vin",
        size=[max(10, p * 50) for p in ota_df["success_probability"]],
        color_discrete_map={"good": "#00D26A", "info": "#4ECDC4", "warning": "#FFB800", "critical": "#FF4B4B"},
    )
    fig_scatter.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
        xaxis_title="Reachability", yaxis_title="Composite",
        margin=dict(l=40, r=20, t=20, b=40), height=320,
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# --- Blockers Detail ---
st.subheader("OTA Blockers & Recommendations")

blocked_vehicles = ota_df[ota_df["success_probability"] <= 0.75].sort_values("success_pct")

if len(blocked_vehicles) > 0:
    for _, row in blocked_vehicles.iterrows():
        sev_icon = {"good": "🟢", "info": "🔵", "warning": "🟡", "critical": "🔴"}.get(row["severity"], "⚪")
        prob_pct = int(row["success_pct"])
        border_color = "#FF4B4B" if prob_pct < 40 else "#FFB800"

        with st.expander(f"{sev_icon} {row['vin']} — {prob_pct}% success | {row['risk_level'].title()}"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Model:** {row['model']}")
                st.markdown(f"**Composite Score:** {row['composite_score']}")
                st.markdown(f"**Will Fail:** {'Yes' if row['will_fail'] else 'No'}")
                if row["risk_factors"]:
                    st.markdown("**Risk Factors:** " + ", ".join(f"`{rf}`" for rf in row["risk_factors"]))
            with col_b:
                st.markdown(f"**Action:** {row['recommended_action']}")
                st.markdown(f"**Reason:** {row['action_reason']}")
                st.markdown(f"**Est. Wait:** {row['estimated_wait']} min")

            if row["customer_message"]:
                st.info(f"💬 {row['customer_message']}")
            if row["technical_details"]:
                with st.expander("Technical Details"):
                    st.code(row["technical_details"])
else:
    st.success("All vehicles are OTA-ready!")

st.divider()

# --- Full Table ---
st.subheader("Full OTA Readiness Table")
display_df = ota_df[["vin", "model", "severity", "success_pct", "risk_level",
                      "will_fail", "recommended_action", "estimated_wait"]].copy()
display_df.columns = ["VIN", "Model", "Severity", "Success %", "Risk Level",
                       "Will Fail", "Action", "Wait (min)"]
st.dataframe(display_df, use_container_width=True, hide_index=True)
