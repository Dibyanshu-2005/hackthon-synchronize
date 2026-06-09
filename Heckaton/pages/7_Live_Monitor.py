"""
Live Monitor - Real-time vehicle health monitoring with auto-refresh.
Shows live score history, degradation detection, and system pulse.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time
from data.engine_client import (
    get_available_vins, get_vehicle_detail, get_vehicle_history,
    get_fleet_metrics, get_engine_health, is_live, get_vehicles,
    get_vehicle_score, COMMANDS, predict_command,
)

st.set_page_config(page_title="Live Monitor", page_icon="📡", layout="wide")

st.markdown("""
<style>
    .monitor-header {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #E74C3C 0%, #F39C12 50%, #00D26A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .live-indicator {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(0,210,106,0.08);
        border: 1px solid rgba(0,210,106,0.2);
        color: #00D26A;
        animation: glow 3s infinite;
    }
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 5px rgba(0,210,106,0.1); }
        50% { box-shadow: 0 0 15px rgba(0,210,106,0.2); }
    }
    .vehicle-tile {
        background: linear-gradient(135deg, #1B2028, #232D3B);
        border: 1px solid #2a3a4a;
        border-radius: 14px;
        padding: 18px;
        text-align: center;
        transition: all 0.3s;
        position: relative;
    }
    .vehicle-tile:hover {
        border-color: #4ECDC4;
        transform: translateY(-2px);
    }
    .score-ring {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 10px;
        font-size: 1.4rem;
        font-weight: 800;
    }
    .degrading-badge {
        position: absolute;
        top: 8px;
        right: 8px;
        background: rgba(255,75,75,0.15);
        border: 1px solid rgba(255,75,75,0.3);
        color: #FF4B4B;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.65rem;
        font-weight: 600;
        animation: blink 1.5s infinite;
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    .timeline-event {
        border-left: 3px solid #2a3a4a;
        padding: 8px 0 8px 16px;
        margin-left: 10px;
        position: relative;
    }
    .timeline-event::before {
        content: '';
        position: absolute;
        left: -6px;
        top: 12px;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: #4ECDC4;
    }
    .monitor-stat {
        background: #1B2028;
        border: 1px solid #2a3a4a;
        border-radius: 10px;
        padding: 14px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
col_h1, col_h2, col_h3 = st.columns([2, 1, 1])

with col_h1:
    st.markdown('<p class="monitor-header">Live Monitor</p>', unsafe_allow_html=True)
    st.caption("Real-time vehicle health tracking with degradation alerts")

with col_h2:
    health = get_engine_health()
    if health:
        st.markdown(f"""
        <div class="live-indicator">
            <span style="width:6px;height:6px;border-radius:50%;background:#00D26A;display:inline-block;"></span>
            LIVE &middot; {health.get('vehicles_loaded', 0)} vehicles
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#FFB800;font-size:0.8rem;">⚠️ Engine offline — showing cached data</span>', unsafe_allow_html=True)

with col_h3:
    auto_refresh = st.toggle("Auto-Refresh (10s)", value=False, key="auto_refresh")

if auto_refresh:
    time.sleep(0.1)
    st.markdown('<meta http-equiv="refresh" content="10">', unsafe_allow_html=True)

st.divider()

# --- Fleet Pulse Overview ---
st.markdown("### Fleet Pulse")

metrics = get_fleet_metrics()
vins = get_available_vins()

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    score = metrics.get("average_score", 0)
    color = "#00D26A" if score > 70 else "#FFB800" if score > 45 else "#FF4B4B"
    st.markdown(f"""
    <div class="monitor-stat">
        <div style="font-size:2rem;font-weight:800;color:{color};">{score:.0f}</div>
        <div style="font-size:0.72rem;color:#8899A6;text-transform:uppercase;">Fleet Score</div>
    </div>
    """, unsafe_allow_html=True)
with col_m2:
    st.markdown(f"""
    <div class="monitor-stat">
        <div style="font-size:2rem;font-weight:800;color:#00D26A;">{metrics.get('healthy_count',0)}</div>
        <div style="font-size:0.72rem;color:#8899A6;text-transform:uppercase;">Healthy</div>
    </div>
    """, unsafe_allow_html=True)
with col_m3:
    st.markdown(f"""
    <div class="monitor-stat">
        <div style="font-size:2rem;font-weight:800;color:#FFB800;">{metrics.get('warning_count',0)}</div>
        <div style="font-size:0.72rem;color:#8899A6;text-transform:uppercase;">Warning</div>
    </div>
    """, unsafe_allow_html=True)
with col_m4:
    st.markdown(f"""
    <div class="monitor-stat">
        <div style="font-size:2rem;font-weight:800;color:#FF4B4B;">{metrics.get('critical_count',0)}</div>
        <div style="font-size:0.72rem;color:#8899A6;text-transform:uppercase;">Critical</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")

# --- Vehicle Tiles Grid ---
st.markdown("### Vehicle Status Grid")

vehicles_resp = get_vehicles()
vehicles_list = vehicles_resp.get("vehicles", [])

if vehicles_list:
    cols_per_row = min(len(vehicles_list), 5)
    cols = st.columns(cols_per_row)

    for idx, v in enumerate(vehicles_list):
        col = cols[idx % cols_per_row]
        vin = v.get("vin", "?")
        score = v.get("composite_score", 0)
        status = v.get("status", "unknown")

        if status in ("critical", "high"):
            ring_color = "#FF4B4B"
            ring_bg = "rgba(255,75,75,0.15)"
            border_color = "#FF4B4B"
        elif status in ("warning", "medium"):
            ring_color = "#FFB800"
            ring_bg = "rgba(255,184,0,0.15)"
            border_color = "#FFB800"
        else:
            ring_color = "#00D26A"
            ring_bg = "rgba(0,210,106,0.15)"
            border_color = "#00D26A"

        top_risk = v.get("top_risk", None)
        risk_count = v.get("risk_factor_count", 0)

        with col:
            st.markdown(f"""
            <div class="vehicle-tile" style="border-top: 3px solid {border_color};">
                <div class="score-ring" style="background:{ring_bg};color:{ring_color};border:2px solid {ring_color};">
                    {score}
                </div>
                <div style="font-weight:700;color:#E8E8E8;font-size:0.85rem;">{vin}</div>
                <div style="font-size:0.7rem;color:#8899A6;">{v.get('model','')}</div>
                {f'<div style="font-size:0.65rem;color:#FF8888;margin-top:4px;">⚠️ {top_risk}</div>' if top_risk else ''}
                {f'<div class="degrading-badge">DEGRADING</div>' if risk_count > 2 else ''}
            </div>
            """, unsafe_allow_html=True)
            st.markdown("")

st.divider()

# --- Score History Chart ---
st.markdown("### Score History")

selected_monitor_vin = st.selectbox("Track Vehicle", vins, key="monitor_vin")

history = get_vehicle_history(selected_monitor_vin)

if history and history.get("history"):
    hist_points = history["history"]
    hist_df = pd.DataFrame(hist_points)

    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(
        x=list(range(len(hist_df))),
        y=hist_df["composite_score"],
        mode="lines+markers",
        name="Composite",
        line=dict(color="#4ECDC4", width=3),
        marker=dict(size=6),
        fill="tozeroy",
        fillcolor="rgba(78,205,196,0.08)",
    ))
    if "reachability_score" in hist_df.columns:
        fig_hist.add_trace(go.Scatter(
            x=list(range(len(hist_df))),
            y=hist_df["reachability_score"],
            mode="lines+markers",
            name="Reachability",
            line=dict(color="#9B59B6", width=2, dash="dot"),
            marker=dict(size=4),
        ))
    if "command_probability" in hist_df.columns:
        fig_hist.add_trace(go.Scatter(
            x=list(range(len(hist_df))),
            y=[p * 100 for p in hist_df["command_probability"]],
            mode="lines+markers",
            name="Cmd Probability",
            line=dict(color="#F39C12", width=2, dash="dash"),
            marker=dict(size=4),
        ))

    fig_hist.add_hline(y=75, line_dash="dot", line_color="rgba(0,210,106,0.3)")
    fig_hist.add_hline(y=35, line_dash="dot", line_color="rgba(255,75,75,0.3)")

    fig_hist.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
        height=300,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis_title="Time (polling intervals)",
        yaxis_title="Score",
        yaxis_range=[0, 100],
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_hist, use_container_width=True)
else:
    st.info("No history available yet. Start the Guardian Engine and simulator for live tracking.")

    # Show simulated trend with mock data
    import numpy as np
    np.random.seed(42)
    mock_hist = pd.DataFrame({
        "time": range(20),
        "composite": np.clip(70 + np.cumsum(np.random.randn(20) * 3), 10, 100),
        "reachability": np.clip(65 + np.cumsum(np.random.randn(20) * 4), 5, 100),
    })

    fig_mock = go.Figure()
    fig_mock.add_trace(go.Scatter(
        x=mock_hist["time"], y=mock_hist["composite"],
        mode="lines+markers", name="Composite (simulated)",
        line=dict(color="#4ECDC4", width=3), fill="tozeroy", fillcolor="rgba(78,205,196,0.08)",
    ))
    fig_mock.add_trace(go.Scatter(
        x=mock_hist["time"], y=mock_hist["reachability"],
        mode="lines", name="Reachability (simulated)",
        line=dict(color="#9B59B6", width=2, dash="dot"),
    ))
    fig_mock.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
        height=280, margin=dict(l=40, r=20, t=20, b=40),
        yaxis_range=[0, 100], yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_mock, use_container_width=True)

st.divider()

# --- Quick Predict All ---
st.markdown("### Quick Health Check")
st.caption("Run a prediction sweep for all vehicles on a specific command")

sweep_cmd = st.selectbox("Command", COMMANDS, format_func=lambda x: x.replace("_", " ").title(), key="sweep_cmd")

if st.button("🔍 Run Sweep", key="sweep_run"):
    sweep_results = []
    for vin in vins:
        r = predict_command(vin, sweep_cmd)
        p = r.get("prediction", {})
        a = r.get("recommended_action", {})
        prob = p.get("success_probability", 0)
        prob_pct = prob * 100 if isinstance(prob, (int, float)) and prob <= 1 else prob
        sweep_results.append({
            "VIN": vin,
            "Probability": round(prob_pct, 1),
            "Risk": p.get("risk_level", "?"),
            "Will Fail": "Yes" if p.get("will_likely_fail") else "No",
            "Action": a.get("display_label", "?"),
            "Factors": ", ".join(p.get("risk_factors", [])[:2]) or "None",
        })

    sweep_df = pd.DataFrame(sweep_results)

    fig_sweep = go.Figure()
    colors = ["#00D26A" if v > 75 else "#FFB800" if v > 40 else "#FF4B4B" for v in sweep_df["Probability"]]
    fig_sweep.add_trace(go.Bar(
        x=sweep_df["VIN"], y=sweep_df["Probability"],
        marker_color=colors,
        text=[f"{v:.0f}%" for v in sweep_df["Probability"]],
        textposition="outside",
    ))
    fig_sweep.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
        height=250, margin=dict(l=40, r=20, t=20, b=40),
        yaxis_range=[0, 110], yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(fig_sweep, use_container_width=True)
    st.dataframe(sweep_df, use_container_width=True, hide_index=True)
