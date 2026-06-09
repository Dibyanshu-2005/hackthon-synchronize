"""
Predictive Connected Experience Guardian - Dashboard Platform
Main entry point: Fleet Overview with live Guardian Engine integration.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data.engine_client import (
    get_fleet_metrics, get_fleet_at_risk, get_vehicles,
    get_engine_health, is_live, get_available_vins, predict_command, COMMANDS,
)
from data.mock_data import get_fleet_dataframe, get_command_history

st.set_page_config(
    page_title="Connected Experience Guardian",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    .main-header {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1B6B93 0%, #4ECDC4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
        letter-spacing: -0.5px;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #8899A6;
        margin-bottom: 1.5rem;
        font-weight: 300;
    }
    .engine-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .engine-live {
        background: rgba(0, 210, 106, 0.12);
        border: 1px solid rgba(0, 210, 106, 0.3);
        color: #00D26A;
    }
    .engine-offline {
        background: rgba(255, 184, 0, 0.12);
        border: 1px solid rgba(255, 184, 0, 0.3);
        color: #FFB800;
    }
    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    .pulse-green {
        background: #00D26A;
        box-shadow: 0 0 6px #00D26A;
    }
    .pulse-yellow {
        background: #FFB800;
        box-shadow: 0 0 6px #FFB800;
    }
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.3); }
        100% { opacity: 1; transform: scale(1); }
    }
    .kpi-card {
        background: linear-gradient(135deg, #1B2028 0%, #232D3B 100%);
        border: 1px solid #2a3a4a;
        border-radius: 16px;
        padding: 20px 18px;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .kpi-card:hover {
        border-color: #1B6B93;
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(27, 107, 147, 0.15);
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        border-radius: 16px 16px 0 0;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 8px 0 4px 0;
    }
    .kpi-label {
        font-size: 0.78rem;
        color: #8899A6;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 500;
    }
    .risk-card {
        background: linear-gradient(135deg, #1B2028 0%, #2a1a1a 100%);
        border: 1px solid #3a2a2a;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 10px;
        transition: all 0.2s ease;
    }
    .risk-card:hover {
        border-color: #FF4B4B;
        background: linear-gradient(135deg, #1B2028 0%, #3a1a1a 100%);
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #E8E8E8;
        margin: 1.5rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .section-title::after {
        content: '';
        flex: 1;
        height: 1px;
        background: linear-gradient(to right, #2a3a4a, transparent);
    }
    .sim-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 500;
        background: rgba(27, 107, 147, 0.1);
        border: 1px solid rgba(27, 107, 147, 0.2);
        color: #4ECDC4;
    }
</style>
""", unsafe_allow_html=True)

# --- Header with Engine Status ---
col_title, col_status = st.columns([3, 1])

with col_title:
    st.markdown('<p class="main-header">Predictive Connected Experience Guardian</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Proactive intelligence layer for connected vehicle customer experience</p>', unsafe_allow_html=True)

with col_status:
    health = get_engine_health()
    if health:
        vehicles_loaded = health.get("vehicles_loaded", 0)
        sim_status = health.get("simulator_bridge", "disconnected")
        badge_class = "engine-live"
        dot_class = "pulse-green"
        label = f"ENGINE LIVE &middot; {vehicles_loaded} vehicles"
        st.markdown(f"""
            <div style="text-align: right; margin-top: 1rem;">
                <span class="engine-badge {badge_class}">
                    <span class="pulse-dot {dot_class}"></span>
                    {label}
                </span>
                <br/>
                <span class="sim-badge" style="margin-top: 6px; display: inline-flex;">
                    {"⚡" if sim_status == "running" else "⏸️"} Simulator: {sim_status}
                </span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style="text-align: right; margin-top: 1rem;">
                <span class="engine-badge engine-offline">
                    <span class="pulse-dot pulse-yellow"></span>
                    DEMO MODE &middot; Mock Data
                </span>
            </div>
        """, unsafe_allow_html=True)

# --- Fleet Metrics KPIs ---
metrics = get_fleet_metrics()
fleet = get_fleet_dataframe()
cmd_history = get_command_history()

col1, col2, col3, col4, col5 = st.columns(5)

kpi_data = [
    ("Composite Score", f"{metrics['average_score']:.0f}", "/100", "#4ECDC4"),
    ("Total Vehicles", str(metrics["total_vehicles"]), "monitored", "#1B6B93"),
    ("Healthy", str(metrics["healthy_count"]), "vehicles", "#00D26A"),
    ("At Risk", str(metrics["at_risk_count"]), "need attention", "#FFB800"),
    ("Critical", str(metrics["critical_count"]), "immediate action", "#FF4B4B"),
]

for col, (label, value, sub, color) in zip([col1, col2, col3, col4, col5], kpi_data):
    with col:
        st.markdown(f"""
        <div class="kpi-card" style="border-top: 3px solid {color};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color: {color};">{value}</div>
            <div style="font-size: 0.7rem; color: #667; margin-top: 2px;">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("")

# --- Fleet Health Scatter + At Risk Panel ---
st.markdown('<div class="section-title">Fleet Health Overview</div>', unsafe_allow_html=True)

col_left, col_right = st.columns([2.2, 1])

with col_left:
    fig = px.scatter(
        fleet,
        x="connectivity_score",
        y="composite_score",
        size="risk_factor_count",
        color="status",
        hover_name="vin",
        hover_data=["model", "region", "ecu_health_score", "vehicle_health_score"],
        color_discrete_map={
            "healthy": "#00D26A",
            "warning": "#FFB800",
            "critical": "#FF4B4B",
        },
        size_max=28,
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
        xaxis_title="Connectivity Score",
        yaxis_title="Composite Score",
        xaxis=dict(range=[0, 100], gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.05)"),
        yaxis=dict(range=[0, 100], gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.05)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=30, b=40),
        height=380,
    )
    fig.add_hrect(y0=0, y1=35, fillcolor="rgba(255,75,75,0.04)", line_width=0)
    fig.add_hrect(y0=35, y1=60, fillcolor="rgba(255,184,0,0.03)", line_width=0)
    fig.add_hrect(y0=60, y1=100, fillcolor="rgba(0,210,106,0.03)", line_width=0)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.markdown('<div class="section-title" style="font-size: 1.1rem;">At-Risk Vehicles</div>', unsafe_allow_html=True)

    at_risk_data = get_fleet_at_risk()
    vehicles_at_risk = at_risk_data.get("vehicles", [])

    if vehicles_at_risk:
        for v in vehicles_at_risk[:5]:
            severity = v.get("severity", "warning")
            if isinstance(severity, str):
                sev_color = "#FF4B4B" if severity == "critical" else "#FFB800"
                sev_icon = "🔴" if severity == "critical" else "🟡"
            else:
                sev_color = "#FFB800"
                sev_icon = "🟡"
            score = v.get("composite_score", 0)
            top_risk = v.get("top_risk", "unknown")
            st.markdown(f"""
            <div class="risk-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 600; color: #E8E8E8;">{sev_icon} {v['vin']}</span>
                    <span style="color: {sev_color}; font-weight: 700; font-size: 1.1rem;">{score}</span>
                </div>
                <div style="font-size: 0.75rem; color: #8899A6; margin-top: 4px;">
                    Risk: <code style="background: rgba(255,75,75,0.1); color: #FF8888; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">{top_risk}</code>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("All vehicles healthy!")

# --- Score Breakdown Radar ---
st.markdown('<div class="section-title">Score Breakdown Radar</div>', unsafe_allow_html=True)

col_radar, col_dist = st.columns([1.5, 1])

with col_radar:
    fig_scores = go.Figure()
    for _, row in fleet.iterrows():
        color_map = {"healthy": "rgba(0,210,106,0.5)", "warning": "rgba(255,184,0,0.5)", "critical": "rgba(255,75,75,0.5)"}
        fig_scores.add_trace(go.Scatterpolar(
            r=[row["composite_score"], row["connectivity_score"], row["ecu_health_score"],
               row["command_history_score"], row["vehicle_health_score"]],
            theta=["Composite", "Connectivity", "ECU Health", "Cmd History", "Vehicle Health"],
            fill="toself",
            name=row["vin"],
            opacity=0.6,
            line=dict(color=color_map.get(row["status"], "rgba(255,255,255,0.3)")),
        ))
    fig_scores.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(255,255,255,0.08)"),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            bgcolor="rgba(0,0,0,0)",
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
        height=380,
        margin=dict(l=60, r=60, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, font_size=10),
        showlegend=True,
    )
    st.plotly_chart(fig_scores, use_container_width=True)

with col_dist:
    st.markdown("**Status Distribution**")
    status_counts = fleet["status"].value_counts()
    fig_pie = go.Figure(data=[go.Pie(
        labels=status_counts.index,
        values=status_counts.values,
        hole=0.55,
        marker=dict(colors=["#00D26A" if s == "healthy" else "#FFB800" if s == "warning" else "#FF4B4B" for s in status_counts.index]),
        textinfo="label+percent",
        textfont_size=12,
    )])
    fig_pie.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
        height=260,
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    success_rate = cmd_history["success"].mean() * 100
    avg_latency = cmd_history["latency_seconds"].mean()
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1B2028, #232D3B); border-radius: 12px; padding: 16px; border: 1px solid #2a3a4a;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="color: #8899A6; font-size: 0.8rem;">48h Cmd Success</span>
            <span style="color: #00D26A; font-weight: 700;">{success_rate:.1f}%</span>
        </div>
        <div style="display: flex; justify-content: space-between;">
            <span style="color: #8899A6; font-size: 0.8rem;">Avg Latency</span>
            <span style="color: #4ECDC4; font-weight: 700;">{avg_latency:.1f}s</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Fleet Table ---
st.markdown('<div class="section-title">Fleet Details</div>', unsafe_allow_html=True)

display_df = fleet[["vin", "model", "region", "status", "composite_score",
                     "connectivity_score", "ecu_health_score", "command_history_score",
                     "vehicle_health_score", "risk_factor_count", "top_risk"]].copy()
display_df.columns = ["VIN", "Model", "Region", "Status", "Composite", "Connectivity",
                       "ECU Health", "Cmd History", "Vehicle Health", "Risk Factors", "Top Risk"]

st.dataframe(
    display_df.style
    .background_gradient(subset=["Composite", "Connectivity", "ECU Health", "Cmd History", "Vehicle Health"], cmap="RdYlGn", vmin=0, vmax=100)
    .background_gradient(subset=["Risk Factors"], cmap="RdYlGn_r"),
    use_container_width=True,
    hide_index=True,
    height=320,
)

# --- Footer ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #556; font-size: 0.75rem; padding: 10px 0;">
    Predictive Connected Experience Guardian &middot; Hackathon 2026 &middot; Real-time ML Intelligence for Connected Vehicles
</div>
""", unsafe_allow_html=True)
