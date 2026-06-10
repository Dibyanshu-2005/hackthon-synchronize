"""
Predictive Connected Experience Guardian
Main view: Fleet health at a glance — what needs attention RIGHT NOW.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data.engine_client import (
    get_fleet_metrics, get_fleet_at_risk, get_engine_health, is_live,
)
from data.mock_data import get_fleet_dataframe, get_command_history

st.set_page_config(
    page_title="Connected Experience Guardian",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Global CSS ---
st.markdown("""<style>
.main-header {font-size:2.2rem;font-weight:800;background:linear-gradient(135deg,#1B6B93,#4ECDC4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:0;}
.sub-header {font-size:0.95rem;color:#8899A6;margin-bottom:1.5rem;}
.kpi-card {background:linear-gradient(135deg,#1B2028,#232D3B);border:1px solid #2a3a4a;border-radius:14px;padding:18px 16px;text-align:center;}
.kpi-value {font-size:2rem;font-weight:800;margin:6px 0 2px 0;}
.kpi-label {font-size:0.72rem;color:#8899A6;text-transform:uppercase;letter-spacing:0.8px;}
</style>""", unsafe_allow_html=True)

# --- Header ---
col_title, col_badge = st.columns([3, 1])
with col_title:
    st.markdown('<p class="main-header">Connected Experience Guardian</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Proactive intelligence for connected vehicle customer experience</p>', unsafe_allow_html=True)
with col_badge:
    health = get_engine_health()
    if health:
        n = health.get("vehicles_loaded", 0)
        st.success(f"ENGINE LIVE — {n} vehicles")
    else:
        st.warning("DEMO MODE")

# --- KPIs ---
metrics = get_fleet_metrics()
fleet = get_fleet_dataframe()
cmd_history = get_command_history()
success_rate = cmd_history["success"].mean() * 100

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Fleet Health", f"{metrics['average_score']:.0f}/100")
with col2:
    st.metric("Vehicles Monitored", metrics["total_vehicles"])
with col3:
    st.metric("Cmd Success (48h)", f"{success_rate:.1f}%")
with col4:
    st.metric("Needs Attention", metrics["at_risk_count"])

st.divider()

# --- Two columns: Fleet status + Alerts ---
col_left, col_right = st.columns([2, 1.2])

with col_left:
    st.markdown("#### Fleet Status")

    for _, row in fleet.iterrows():
        if row["status"] == "healthy":
            dot = "🟢"
        elif row["status"] == "warning":
            dot = "🟡"
        else:
            dot = "🔴"

        score = row["composite_score"]
        score_color = "#00D26A" if score > 85 else "#FFB800" if score > 60 else "#FF4B4B"
        vin_short = row["vin"][:11] + "..." + row["vin"][-4:]

        risk_html = ""
        if row["risk_factor_count"] > 0:
            risk_html = f' — <code>{row["top_risk"]}</code>'

        st.markdown(
            f'{dot} **{vin_short}** ({row["model"]}) — '
            f'<span style="color:{score_color};font-weight:700;font-size:1.2rem;">{score:.0f}</span>'
            f'{risk_html}',
            unsafe_allow_html=True
        )

with col_right:
    st.markdown("#### ⚠️ Attention Required")

    at_risk = get_fleet_at_risk()
    vehicles_at_risk = at_risk.get("vehicles", [])

    if vehicles_at_risk:
        for v in vehicles_at_risk:
            severity = v.get("severity", "warning")
            icon = "🔴" if severity == "critical" else "🟡"
            vin_short = v["vin"][:11] + "..." + v["vin"][-4:]
            st.markdown(
                f'{icon} **{vin_short}** — Score: **{v["composite_score"]:.0f}**/100\n\n'
                f'> Risk: `{v.get("top_risk", "—")}`'
            )
    else:
        st.success("All vehicles healthy — no action needed.")

st.divider()

# --- Score Overview Chart ---
st.markdown("#### Fleet Composite Scores")

fig = go.Figure()
fig.add_trace(go.Bar(
    x=[v[:7] + "..." + v[-4:] for v in fleet["vin"]],
    y=fleet["composite_score"],
    marker_color=["#00D26A" if s == "healthy" else "#FFB800" if s == "warning" else "#FF4B4B" for s in fleet["status"]],
    text=[f"{v:.0f}" for v in fleet["composite_score"]],
    textposition="outside",
    textfont_size=12,
))
fig.add_hline(y=75, line_dash="dot", line_color="rgba(255,184,0,0.5)", annotation_text="Attention Threshold", annotation_position="right")
fig.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="#FAFAFA",
    yaxis_range=[0, 110],
    yaxis_title="Composite Score",
    xaxis_title="",
    margin=dict(l=40, r=20, t=10, b=60),
    height=300,
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)
