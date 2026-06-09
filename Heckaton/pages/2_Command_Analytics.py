"""Command Analytics - Success rates, latency, failure patterns across fleet."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data.mock_data import get_command_history, get_all_predictions, COMMANDS
from data.engine_client import is_live

st.set_page_config(page_title="Command Analytics", page_icon="📊", layout="wide")

st.markdown("""
<style>
    .analytics-header {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1B6B93 0%, #4ECDC4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stat-card {
        background: linear-gradient(135deg, #1B2028, #232D3B);
        border: 1px solid #2a3a4a;
        border-radius: 14px;
        padding: 18px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="analytics-header">Command Analytics</p>', unsafe_allow_html=True)
st.caption(f"{'🟢 Live Engine' if is_live() else '🟡 Demo Mode'} | 48-hour command execution analysis")

cmd_history = get_command_history(hours=48)

# --- Top metrics ---
col1, col2, col3, col4 = st.columns(4)

total_cmds = len(cmd_history)
success_rate = cmd_history["success"].mean() * 100
avg_latency = cmd_history["latency_seconds"].mean()
failed_cmds = len(cmd_history[~cmd_history["success"]])

metrics_data = [
    ("Total Commands", str(total_cmds), "#4ECDC4"),
    ("Success Rate", f"{success_rate:.1f}%", "#00D26A"),
    ("Avg Latency", f"{avg_latency:.1f}s", "#1B6B93"),
    ("Failed", str(failed_cmds), "#FF4B4B"),
]

for col, (label, value, color) in zip([col1, col2, col3, col4], metrics_data):
    with col:
        st.markdown(f"""
        <div class="stat-card" style="border-top: 3px solid {color};">
            <div style="font-size:1.8rem;font-weight:800;color:{color};">{value}</div>
            <div style="font-size:0.72rem;color:#8899A6;text-transform:uppercase;letter-spacing:1px;">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# --- Success by command type ---
st.subheader("Success Rate by Command")
cmd_stats = cmd_history.groupby("command").agg(
    total=("success", "count"),
    success_rate=("success", "mean"),
    avg_latency=("latency_seconds", "mean"),
).reset_index()
cmd_stats["success_rate"] = cmd_stats["success_rate"] * 100
cmd_stats["command_label"] = cmd_stats["command"].str.replace("_", " ").str.title()

colors = ["#00D26A" if v > 75 else "#FFB800" if v > 50 else "#FF4B4B" for v in cmd_stats["success_rate"]]
fig_cmd = go.Figure()
fig_cmd.add_trace(go.Bar(
    x=cmd_stats.sort_values("success_rate")["command_label"],
    y=cmd_stats.sort_values("success_rate")["success_rate"],
    marker_color=["#00D26A" if v > 75 else "#FFB800" if v > 50 else "#FF4B4B"
                  for v in cmd_stats.sort_values("success_rate")["success_rate"]],
    text=[f"{v:.1f}%" for v in cmd_stats.sort_values("success_rate")["success_rate"]],
    textposition="outside",
))
fig_cmd.update_layout(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
    yaxis_range=[0, 110], xaxis_title="", yaxis_title="Success Rate %",
    margin=dict(l=40, r=20, t=20, b=60), height=320,
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
)
st.plotly_chart(fig_cmd, use_container_width=True)

# --- Latency + Failure Reasons ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Latency Distribution")
    fig_lat = px.histogram(
        cmd_history, x="latency_seconds", color="success",
        color_discrete_map={True: "#00D26A", False: "#FF4B4B"},
        nbins=30, labels={"success": "Succeeded"},
    )
    fig_lat.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
        xaxis_title="Latency (seconds)", yaxis_title="Count",
        margin=dict(l=40, r=20, t=20, b=40), height=280,
    )
    st.plotly_chart(fig_lat, use_container_width=True)

with col_right:
    st.subheader("Top Failure Reasons")
    failures = cmd_history[cmd_history["failure_reason"].notna()]
    if len(failures) > 0:
        reason_counts = failures["failure_reason"].value_counts().head(8)
        fig_reasons = go.Figure()
        fig_reasons.add_trace(go.Bar(
            x=reason_counts.values, y=reason_counts.index,
            orientation="h",
            marker_color=["#FF4B4B" if v > 10 else "#FFB800" for v in reason_counts.values],
        ))
        fig_reasons.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
            xaxis_title="Count", yaxis_title="",
            margin=dict(l=120, r=20, t=20, b=40), height=280,
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_reasons, use_container_width=True)
    else:
        st.success("No failures recorded!")

st.divider()

# --- Trend ---
st.subheader("Command Latency & Success Trend")
cmd_history["hour"] = cmd_history["timestamp"].dt.floor("h")
hourly = cmd_history.groupby("hour").agg(
    avg_latency=("latency_seconds", "mean"),
    success_rate=("success", "mean"),
    count=("success", "count"),
).reset_index()
hourly["success_rate"] = hourly["success_rate"] * 100

fig_trend = go.Figure()
fig_trend.add_trace(go.Scatter(
    x=hourly["hour"], y=hourly["avg_latency"],
    mode="lines+markers", name="Avg Latency (s)",
    line=dict(color="#1B6B93", width=2), marker=dict(size=4),
))
fig_trend.add_trace(go.Scatter(
    x=hourly["hour"], y=hourly["success_rate"],
    mode="lines+markers", name="Success Rate %",
    yaxis="y2", line=dict(color="#00D26A", width=2), marker=dict(size=4),
))
fig_trend.update_layout(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
    yaxis=dict(title="Avg Latency (s)", side="left", gridcolor="rgba(255,255,255,0.05)"),
    yaxis2=dict(title="Success Rate %", side="right", overlaying="y", range=[0, 100]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=50, r=50, t=30, b=40), height=300,
)
st.plotly_chart(fig_trend, use_container_width=True)

# --- Per vehicle ---
st.subheader("Success Rate by Vehicle")
vehicle_stats = cmd_history.groupby("vin").agg(
    success_rate=("success", "mean"),
    avg_latency=("latency_seconds", "mean"),
    total=("success", "count"),
).reset_index()
vehicle_stats["success_rate"] = vehicle_stats["success_rate"] * 100

fig_v = go.Figure()
fig_v.add_trace(go.Bar(
    x=vehicle_stats.sort_values("success_rate")["vin"],
    y=vehicle_stats.sort_values("success_rate")["success_rate"],
    marker_color=["#00D26A" if v > 75 else "#FFB800" if v > 50 else "#FF4B4B"
                  for v in vehicle_stats.sort_values("success_rate")["success_rate"]],
    text=[f"{v:.0f}%" for v in vehicle_stats.sort_values("success_rate")["success_rate"]],
    textposition="outside",
))
fig_v.update_layout(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
    yaxis_range=[0, 110], xaxis_title="", yaxis_title="Success Rate %",
    margin=dict(l=40, r=20, t=20, b=40), height=280,
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
)
st.plotly_chart(fig_v, use_container_width=True)

# --- Predicted vs Historical ---
st.divider()
st.subheader("Predicted vs Historical Success")
st.caption("Guardian Engine predictions vs actual 48h command history")

predictions = get_all_predictions()
pred_by_cmd = predictions.groupby("command")["success_probability"].mean().reset_index()
pred_by_cmd["success_probability"] = pred_by_cmd["success_probability"] * 100
pred_by_cmd.columns = ["command", "predicted"]

hist_by_cmd = cmd_history.groupby("command")["success"].mean().reset_index()
hist_by_cmd["success"] = hist_by_cmd["success"] * 100
hist_by_cmd.columns = ["command", "historical"]

comparison = pred_by_cmd.merge(hist_by_cmd, on="command")
comparison["command_label"] = comparison["command"].str.replace("_", " ").str.title()

fig_comp = go.Figure()
fig_comp.add_trace(go.Bar(name="Predicted", x=comparison["command_label"], y=comparison["predicted"], marker_color="#4ECDC4"))
fig_comp.add_trace(go.Bar(name="Historical", x=comparison["command_label"], y=comparison["historical"], marker_color="#00D26A"))
fig_comp.update_layout(
    barmode="group",
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
    yaxis_range=[0, 100], yaxis_title="Success %",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=40, r=20, t=30, b=40), height=300,
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
)
st.plotly_chart(fig_comp, use_container_width=True)
