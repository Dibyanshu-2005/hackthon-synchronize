"""Business Insights - Executive dashboard with scores, risk distribution, and impact analysis."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data.mock_data import get_fleet_dataframe, get_all_predictions, get_command_history
from data.engine_client import get_fleet_at_risk, get_fleet_metrics, is_live

st.set_page_config(page_title="Business Insights", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .biz-header {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #F39C12 0%, #E74C3C 50%, #9B59B6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="biz-header">Business Insights</p>', unsafe_allow_html=True)
st.caption(f"{'🟢 Live Engine' if is_live() else '🟡 Demo Mode'} | Executive view — service reliability, risk distribution, customer impact")

fleet = get_fleet_dataframe()
cmd_history = get_command_history(hours=48)
predictions = get_all_predictions()
metrics = get_fleet_metrics()
at_risk = get_fleet_at_risk()

# --- Executive KPIs ---
col1, col2, col3, col4 = st.columns(4)

fleet_composite = metrics.get("average_score", fleet["composite_score"].mean())
service_reliability = cmd_history["success"].mean() * 100
at_risk_count = at_risk.get("at_risk_count", 0)
at_risk_pct = at_risk_count / max(metrics.get("total_vehicles", len(fleet)), 1) * 100
avg_confidence = predictions["confidence"].mean() * 100

kpi_data = [
    ("Fleet Score", f"{fleet_composite:.0f}/100", "#4ECDC4"),
    ("Reliability", f"{service_reliability:.1f}%", "#00D26A"),
    ("At-Risk", f"{at_risk_pct:.0f}%", "#FFB800"),
    ("Pred. Confidence", f"{avg_confidence:.0f}%", "#9B59B6"),
]

for col, (label, value, color) in zip([col1, col2, col3, col4], kpi_data):
    with col:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1B2028,#232D3B);border:1px solid #2a3a4a;border-radius:14px;padding:18px;text-align:center;border-top:3px solid {color};">
            <div style="font-size:1.8rem;font-weight:800;color:{color};">{value}</div>
            <div style="font-size:0.72rem;color:#8899A6;text-transform:uppercase;letter-spacing:1px;">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# --- Score Heatmap ---
st.subheader("Score Heatmap — All Dimensions")

heatmap_data = fleet[["vin", "composite_score", "connectivity_score", "ecu_health_score",
                       "command_history_score", "vehicle_health_score"]].set_index("vin")
heatmap_data.columns = ["Composite", "Connectivity", "ECU Health", "Cmd History", "Vehicle Health"]

fig_heatmap = px.imshow(
    heatmap_data.values,
    x=heatmap_data.columns.tolist(),
    y=heatmap_data.index.tolist(),
    color_continuous_scale=["#FF4B4B", "#FFB800", "#00D26A"],
    zmin=0, zmax=100,
    labels={"color": "Score"},
)
fig_heatmap.update_layout(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
    height=300, margin=dict(l=80, r=20, t=20, b=40),
)
st.plotly_chart(fig_heatmap, use_container_width=True)

# --- Prediction Heatmap ---
st.subheader("Prediction Heatmap — Vehicle x Command")

pred_pivot = predictions.pivot_table(values="success_probability", index="vin", columns="command", aggfunc="mean")
pred_pivot = pred_pivot * 100

fig_pred_heat = px.imshow(
    pred_pivot.values,
    x=[c.replace("_", " ").title() for c in pred_pivot.columns],
    y=pred_pivot.index.tolist(),
    color_continuous_scale=["#FF4B4B", "#FFB800", "#00D26A"],
    zmin=0, zmax=100,
    labels={"color": "Success %"},
)
fig_pred_heat.update_layout(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
    height=320, margin=dict(l=80, r=20, t=20, b=40),
)
st.plotly_chart(fig_pred_heat, use_container_width=True)

st.divider()

# --- Regional + Model Analysis ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Performance by Region")
    region_stats = fleet.groupby("region").agg(
        avg_composite=("composite_score", "mean"),
        avg_connectivity=("connectivity_score", "mean"),
        avg_ecu=("ecu_health_score", "mean"),
        vehicle_count=("vin", "count"),
    ).reset_index()

    fig_region = go.Figure()
    fig_region.add_trace(go.Bar(name="Composite", x=region_stats["region"], y=region_stats["avg_composite"], marker_color="#4ECDC4"))
    fig_region.add_trace(go.Bar(name="Connectivity", x=region_stats["region"], y=region_stats["avg_connectivity"], marker_color="#00D26A"))
    fig_region.add_trace(go.Bar(name="ECU Health", x=region_stats["region"], y=region_stats["avg_ecu"], marker_color="#FFB800"))
    fig_region.update_layout(
        barmode="group",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
        yaxis_range=[0, 100], yaxis_title="Score",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=30, b=40), height=300,
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(fig_region, use_container_width=True)

with col_right:
    st.subheader("Performance by Model")
    model_stats = fleet.groupby("model").agg(
        avg_composite=("composite_score", "mean"),
        avg_connectivity=("connectivity_score", "mean"),
        vehicle_count=("vin", "count"),
    ).reset_index()

    fig_model = px.scatter(
        model_stats, x="avg_composite", y="avg_connectivity",
        size="vehicle_count", color="model", size_max=30,
    )
    fig_model.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
        xaxis_title="Avg Composite", yaxis_title="Avg Connectivity",
        xaxis_range=[0, 100], yaxis_range=[0, 100],
        margin=dict(l=40, r=20, t=20, b=40), height=300,
    )
    st.plotly_chart(fig_model, use_container_width=True)

st.divider()

# --- Customer Impact ---
st.subheader("Customer Impact Estimation")

col_a, col_b = st.columns(2)

with col_a:
    total_vehicles = metrics.get("total_vehicles", len(fleet))
    impacted = at_risk_count
    critical_v = metrics.get("critical_count", len(fleet[fleet["status"] == "critical"]))

    fig_funnel = go.Figure(go.Funnel(
        y=["Total Fleet", "At Risk", "Critical"],
        x=[total_vehicles, impacted, critical_v],
        marker=dict(color=["#4ECDC4", "#FFB800", "#FF4B4B"]),
        textfont=dict(color="#FAFAFA"),
    ))
    fig_funnel.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
        margin=dict(l=20, r=20, t=20, b=20), height=250,
    )
    st.plotly_chart(fig_funnel, use_container_width=True)

with col_b:
    st.markdown("**Impact Metrics**")
    failed_cmds = len(cmd_history[~cmd_history["success"]])
    preventable = int(failed_cmds * 0.6)
    degrading = len(predictions[predictions["is_degrading"]])
    total_preds = len(predictions)

    metrics_list = [
        ("Commands failed in 48h", str(failed_cmds), "🔴"),
        ("Preventable with Guardian", str(preventable), "🟢"),
        ("Predictions showing degradation", f"{degrading}/{total_preds}", "🟡"),
        ("Est. trust score improvement", "+22 pts", "🟢"),
        ("Avg wait time for queued cmds", f"{predictions['estimated_wait_minutes'].mean():.0f} min", "🔵"),
    ]

    for label, value, icon in metrics_list:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-bottom:1px solid #1a2a3a;">
            <span style="font-size:1.1rem;">{icon}</span>
            <span style="color:#E8E8E8;font-weight:700;min-width:60px;">{value}</span>
            <span style="color:#8899A6;font-size:0.82rem;">{label}</span>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# --- Recommended Actions Distribution ---
st.subheader("Recommended Actions Across Fleet")

action_dist = predictions["action_label"].value_counts()
fig_actions = go.Figure()
fig_actions.add_trace(go.Bar(
    x=action_dist.index, y=action_dist.values,
    marker_color=px.colors.sequential.Tealgrn_r[:len(action_dist)],
    text=action_dist.values, textposition="outside",
))
fig_actions.update_layout(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
    xaxis_title="", yaxis_title="Count",
    margin=dict(l=40, r=20, t=20, b=60), height=280,
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
)
st.plotly_chart(fig_actions, use_container_width=True)
