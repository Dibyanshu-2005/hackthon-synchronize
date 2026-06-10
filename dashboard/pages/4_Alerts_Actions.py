"""Alerts & Preventive Actions - Active alerts with recommended actions and explanations."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data.mock_data import get_alerts, VEHICLE_PROFILES, ACTION_LABELS
from data.engine_client import get_vehicle_explain, get_available_vins, is_live

st.set_page_config(page_title="Alerts & Actions", page_icon="🚨", layout="wide")

st.markdown("""
<style>
    .alerts-header {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FF4B4B 0%, #FFB800 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .alert-card {
        background: linear-gradient(135deg, #1B2028, #232D3B);
        border: 1px solid #2a3a4a;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 12px;
        transition: all 0.2s;
        position: relative;
    }
    .alert-card:hover {
        border-color: #4a5a6a;
    }
    .alert-critical {
        border-left: 4px solid #FF4B4B;
    }
    .alert-warning {
        border-left: 4px solid #FFB800;
    }
    .alert-action-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="alerts-header">Alerts & Preventive Actions</p>', unsafe_allow_html=True)
st.caption(f"{'🟢 Live Engine' if is_live() else '🟡 Demo Mode'} | Proactive issue detection and recommended actions")

alerts = get_alerts()

# --- Summary ---
col1, col2, col3 = st.columns(3)
critical_count = len(alerts[alerts["severity"] == "critical"])
warning_count = len(alerts[alerts["severity"] == "warning"])
degrading_count = len(alerts[alerts["is_degrading"]])

summary_data = [
    ("Critical", str(critical_count), "#FF4B4B"),
    ("Warnings", str(warning_count), "#FFB800"),
    ("Degrading", str(degrading_count), "#9B59B6"),
]

for col, (label, value, color) in zip([col1, col2, col3], summary_data):
    with col:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1B2028,#232D3B);border:1px solid #2a3a4a;border-radius:14px;padding:18px;text-align:center;border-top:3px solid {color};">
            <div style="font-size:2.2rem;font-weight:800;color:{color};">{value}</div>
            <div style="font-size:0.72rem;color:#8899A6;text-transform:uppercase;letter-spacing:1px;">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# --- Filters ---
col_f1, col_f2 = st.columns(2)
with col_f1:
    severity_filter = st.multiselect("Filter by Severity", ["critical", "warning"], default=["critical", "warning"])
with col_f2:
    all_risks = sorted(set(rf for rfs in alerts["risk_factors"] for rf in rfs))
    risk_filter = st.multiselect("Filter by Risk Factor", all_risks, default=[])

filtered = alerts[alerts["severity"].isin(severity_filter)] if severity_filter else alerts
if risk_filter:
    filtered = filtered[filtered["risk_factors"].apply(lambda rfs: any(rf in rfs for rf in risk_filter))]

# --- Alert Cards ---
st.markdown(f"### Active Alerts ({len(filtered)})")

for _, alert in filtered.iterrows():
    sev = alert["severity"]
    card_class = "alert-critical" if sev == "critical" else "alert-warning"
    sev_icon = "🔴" if sev == "critical" else "🟡"
    action_color = "rgba(255,75,75,0.15)" if sev == "critical" else "rgba(255,184,0,0.15)"
    action_border = "rgba(255,75,75,0.3)" if sev == "critical" else "rgba(255,184,0,0.3)"
    action_text_color = "#FF8888" if sev == "critical" else "#FFD666"

    risk_chips = " ".join(
        f'<span style="display:inline-block;padding:2px 8px;border-radius:5px;font-size:0.68rem;background:rgba(255,75,75,0.08);border:1px solid rgba(255,75,75,0.15);color:#FF8888;margin:1px 2px;">{rf}</span>'
        for rf in alert["risk_factors"][:4]
    )

    st.markdown(f"""
    <div class="alert-card {card_class}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
                <div style="font-weight:700;color:#E8E8E8;font-size:1rem;">{sev_icon} {alert['vin']} <span style="font-weight:400;color:#8899A6;">({alert['model']})</span></div>
                <div style="color:#B8C8D8;font-style:italic;margin:6px 0;font-size:0.85rem;">{alert['customer_message']}</div>
                <div style="margin-top:6px;">{risk_chips}</div>
                <div style="font-size:0.7rem;color:#667;margin-top:6px;">
                    {alert['timestamp'].strftime('%H:%M:%S')} &middot; Score: {alert['composite_score']}
                </div>
            </div>
            <div style="text-align:right;">
                <span class="alert-action-badge" style="background:{action_color};border:1px solid {action_border};color:{action_text_color};">
                    {alert['action_label']}
                </span>
                <div style="font-size:0.68rem;color:#667;margin-top:6px;">
                    {'📉 Degrading' if alert['is_degrading'] else ''}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- Alert Analysis ---
st.subheader("Alert Analysis")

col_left, col_right = st.columns(2)

with col_left:
    if len(alerts) > 0:
        risk_exploded = []
        for _, row in alerts.iterrows():
            for rf in row["risk_factors"]:
                risk_exploded.append({"risk_factor": rf, "vin": row["vin"], "severity": row["severity"]})
        risk_df = pd.DataFrame(risk_exploded)
        rf_counts = risk_df["risk_factor"].value_counts()

        fig_rf = go.Figure()
        fig_rf.add_trace(go.Bar(
            x=rf_counts.values, y=rf_counts.index,
            orientation="h",
            marker_color=["#FF4B4B" if v > 3 else "#FFB800" for v in rf_counts.values],
        ))
        fig_rf.update_layout(
            title="Most Common Risk Factors",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
            xaxis_title="Occurrences", yaxis_title="",
            margin=dict(l=140, r=20, t=40, b=40), height=300,
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_rf, use_container_width=True)

with col_right:
    if len(alerts) > 0:
        action_counts = alerts["action_label"].value_counts()
        fig_actions = go.Figure(data=[go.Pie(
            labels=action_counts.index, values=action_counts.values,
            hole=0.5, textinfo="label+percent", textfont_size=10,
            marker=dict(colors=px.colors.sequential.Tealgrn_r[:len(action_counts)]),
        )])
        fig_actions.update_layout(
            title="Recommended Actions",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
            margin=dict(l=20, r=20, t=40, b=20), height=300,
            showlegend=False,
        )
        st.plotly_chart(fig_actions, use_container_width=True)

st.divider()

# --- Explanation Engine Demo ---
st.subheader("Customer Explanation Engine")
st.caption("How technical issues are translated for customers — powered by Guardian Engine")

vins = get_available_vins()
selected_vin = st.selectbox("Select Vehicle to Explain", vins)
explanation = get_vehicle_explain(selected_vin)

if isinstance(explanation, dict) and "error" not in explanation:
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.markdown("**Technical View:**")
        tech = explanation.get("technical_details", "")
        st.code(tech)
        risk_factors = explanation.get("risk_factors", [])
        if risk_factors:
            st.markdown("**Risk Factors:** " + ", ".join(f"`{rf}`" for rf in risk_factors))
        st.markdown(f"**Severity:** {explanation.get('severity', 'N/A')}")

    with col_e2:
        st.markdown("**Customer Sees:**")
        sev = explanation.get("severity", "info")
        sev_icons = {"good": "🟢", "info": "🔵", "warning": "🟡", "critical": "🔴"}
        st.info(f"{sev_icons.get(sev, '⚪')} {explanation.get('customer_message', '')}")
        ts = explanation.get("timestamp", "")
        if ts:
            st.caption(f"Generated at: {ts[:19]}")
