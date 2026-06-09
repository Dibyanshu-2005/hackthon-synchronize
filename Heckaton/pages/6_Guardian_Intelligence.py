"""
Guardian Intelligence - THE killer feature.
Live predictions, what-if simulator, command execution with real engine.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from data.engine_client import (
    predict_command, execute_command, get_available_vins,
    get_vehicle_detail, get_vehicle_explain, is_live, COMMANDS,
)

st.set_page_config(page_title="Guardian Intelligence", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .gi-header {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #9B59B6 0%, #4ECDC4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .prediction-card {
        background: linear-gradient(135deg, #1B2028 0%, #232D3B 100%);
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #2a3a4a;
        position: relative;
        overflow: hidden;
    }
    .prediction-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
        border-radius: 16px 16px 0 0;
    }
    .prob-display {
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        margin: 10px 0;
        line-height: 1;
    }
    .action-button {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 12px 24px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 1rem;
        margin: 8px 0;
        width: 100%;
        justify-content: center;
        transition: all 0.3s ease;
    }
    .action-green {
        background: linear-gradient(135deg, rgba(0,210,106,0.15), rgba(0,210,106,0.05));
        border: 2px solid rgba(0,210,106,0.4);
        color: #00D26A;
    }
    .action-yellow {
        background: linear-gradient(135deg, rgba(255,184,0,0.15), rgba(255,184,0,0.05));
        border: 2px solid rgba(255,184,0,0.4);
        color: #FFB800;
    }
    .action-red {
        background: linear-gradient(135deg, rgba(255,75,75,0.15), rgba(255,75,75,0.05));
        border: 2px solid rgba(255,75,75,0.4);
        color: #FF4B4B;
    }
    .risk-chip {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
        margin: 2px 3px;
        background: rgba(255,75,75,0.1);
        border: 1px solid rgba(255,75,75,0.2);
        color: #FF8888;
    }
    .customer-msg {
        background: linear-gradient(135deg, #1a2a3a, #1a2a4a);
        border: 1px solid #2a4a6a;
        border-left: 4px solid #4ECDC4;
        border-radius: 0 12px 12px 0;
        padding: 16px 20px;
        font-style: italic;
        color: #B8C8D8;
        margin: 12px 0;
    }
    .tech-details {
        background: #0a0f14;
        border: 1px solid #1a2a3a;
        border-radius: 8px;
        padding: 12px 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: #7a9ab8;
        margin-top: 8px;
    }
    .exec-result {
        background: linear-gradient(135deg, #1a2a3a 0%, #1a3a2a 100%);
        border: 2px solid rgba(78, 205, 196, 0.3);
        border-radius: 12px;
        padding: 20px;
        margin-top: 16px;
    }
    .whatif-section {
        background: linear-gradient(135deg, #1B2028, #2a2040);
        border: 1px solid #3a2a5a;
        border-radius: 16px;
        padding: 24px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="gi-header">Guardian Intelligence</p>', unsafe_allow_html=True)
st.markdown("**Real-time predictive intelligence** — Will this command succeed? What should we do?")

live_badge = "🟢 Live Engine" if is_live() else "🟡 Demo Mode"
st.caption(f"{live_badge} | Predictions powered by ML scoring pipeline")

st.divider()

# --- Command Prediction Console ---
st.markdown("### Command Prediction Console")

col_vin, col_cmd, col_run = st.columns([2, 2, 1])

vins = get_available_vins()

with col_vin:
    selected_vin = st.selectbox("Vehicle", vins, key="gi_vin")
with col_cmd:
    selected_cmd = st.selectbox("Command", COMMANDS, format_func=lambda x: x.replace("_", " ").title(), key="gi_cmd")
with col_run:
    st.markdown("")
    st.markdown("")
    predict_btn = st.button("⚡ Predict", type="primary", use_container_width=True)

if predict_btn or st.session_state.get("gi_last_prediction"):
    if predict_btn:
        result = predict_command(selected_vin, selected_cmd)
        st.session_state["gi_last_prediction"] = result
        st.session_state["gi_last_vin"] = selected_vin
        st.session_state["gi_last_cmd"] = selected_cmd
    else:
        result = st.session_state["gi_last_prediction"]

    pred = result.get("prediction", {})
    scores = result.get("scores", {})
    explanation = result.get("explanation", {})
    action = result.get("recommended_action", {})

    success_prob = pred.get("success_probability", 0)
    if isinstance(success_prob, (int, float)):
        prob_pct = int(success_prob * 100) if success_prob <= 1 else int(success_prob)
    else:
        prob_pct = 0

    prob_color = "#00D26A" if prob_pct > 75 else "#FFB800" if prob_pct > 40 else "#FF4B4B"
    action_class = "action-green" if prob_pct > 75 else "action-yellow" if prob_pct > 40 else "action-red"

    col_prob, col_action, col_explain = st.columns([1, 1.2, 1.5])

    with col_prob:
        st.markdown(f"""
        <div class="prediction-card" style="text-align: center;">
            <div style="color: #8899A6; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;">Success Probability</div>
            <div class="prob-display" style="color: {prob_color};">{prob_pct}%</div>
            <div style="font-size: 0.8rem; color: #667;">
                Confidence: {int(pred.get('confidence', pred.get('risk_level', 'N/A')) if isinstance(pred.get('confidence'), (int, float)) else 0)}% |
                {'⚠️ Will Likely Fail' if pred.get('will_likely_fail', False) else '✓ Likely Success'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Score gauges
        st.markdown("")
        score_fields = [
            ("Composite", scores.get("composite_score", 0)),
            ("Reachability", scores.get("reachability_score", scores.get("connectivity_score", 0))),
            ("Data Fresh", scores.get("data_freshness_score", scores.get("ecu_health_score", 0))),
        ]
        for label, val in score_fields:
            val = val if isinstance(val, (int, float)) else 0
            bar_color = "#00D26A" if val > 70 else "#FFB800" if val > 40 else "#FF4B4B"
            st.markdown(f"""
            <div style="margin: 6px 0;">
                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #8899A6;">
                    <span>{label}</span><span style="color: {bar_color}; font-weight: 600;">{val}</span>
                </div>
                <div style="background: #1a2028; border-radius: 4px; height: 6px; overflow: hidden;">
                    <div style="width: {val}%; height: 100%; background: {bar_color}; border-radius: 4px; transition: width 0.5s;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_action:
        action_label = action.get("display_label", "Unknown")
        action_reason = action.get("reason", "")
        wait_min = action.get("estimated_wait_minutes", 0)
        fallback = action.get("fallback_action", None)

        st.markdown(f"""
        <div class="prediction-card">
            <div style="color: #8899A6; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">Recommended Action</div>
            <div class="{action_class} action-button">{action_label}</div>
            <div style="color: #B8C8D8; font-size: 0.85rem; margin-top: 12px;">{action_reason}</div>
            {"<div style='color: #667; font-size: 0.78rem; margin-top: 8px;'>⏱️ Est. wait: " + str(wait_min) + " min</div>" if wait_min else ""}
            {"<div style='color: #556; font-size: 0.72rem; margin-top: 6px;'>Fallback: " + str(fallback).replace('_', ' ').title() + "</div>" if fallback else ""}
        </div>
        """, unsafe_allow_html=True)

        # Execute button
        st.markdown("")
        if st.button("🚀 Execute Command", type="secondary", use_container_width=True, key="exec_cmd"):
            exec_result = execute_command(
                st.session_state.get("gi_last_vin", selected_vin),
                st.session_state.get("gi_last_cmd", selected_cmd)
            )
            status = exec_result.get("status", "unknown")
            message = exec_result.get("message", "Command processed.")
            status_icon = "✅" if status == "executed" else "📋" if status == "queued" else "🚫"
            st.markdown(f"""
            <div class="exec-result">
                <div style="font-size: 1.2rem; font-weight: 700; color: #4ECDC4;">{status_icon} {status.upper()}</div>
                <div style="color: #B8C8D8; margin-top: 8px;">{message}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_explain:
        severity = explanation.get("severity", "info")
        sev_icon = {"good": "🟢", "info": "🔵", "warning": "🟡", "critical": "🔴"}.get(severity, "⚪")
        customer_msg = explanation.get("customer_message", "")
        tech_details = explanation.get("technical_details", "")
        risk_factors = pred.get("risk_factors", [])

        st.markdown(f"""
        <div class="prediction-card">
            <div style="color: #8899A6; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">
                {sev_icon} Explanation &middot; {severity.title()}
            </div>
            <div class="customer-msg">{customer_msg}</div>
            <div class="tech-details">{tech_details}</div>
            <div style="margin-top: 12px;">
                {"".join(f'<span class="risk-chip">{rf}</span>' for rf in risk_factors) if risk_factors else '<span style="color: #4ECDC4; font-size: 0.8rem;">No risk factors detected</span>'}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# --- Multi-Command Comparison ---
st.markdown("### Command Success Heatmap")
st.caption("Predicted success probability for all commands across selected vehicle")

compare_vin = st.selectbox("Compare Vehicle", vins, key="gi_compare_vin")

predictions_data = []
for cmd in COMMANDS:
    pred_result = predict_command(compare_vin, cmd)
    p = pred_result.get("prediction", {})
    prob = p.get("success_probability", 0)
    if isinstance(prob, (int, float)):
        prob_pct = prob * 100 if prob <= 1 else prob
    else:
        prob_pct = 0
    predictions_data.append({
        "Command": cmd.replace("_", " ").title(),
        "Success %": round(prob_pct, 1),
        "Risk Level": p.get("risk_level", "unknown"),
        "Will Fail": p.get("will_likely_fail", False),
        "Latency (ms)": p.get("estimated_latency_ms", None),
    })

pred_df = pd.DataFrame(predictions_data)

col_chart, col_table = st.columns([1.5, 1])

with col_chart:
    fig_bar = go.Figure()
    colors = ["#00D26A" if v > 75 else "#FFB800" if v > 40 else "#FF4B4B" for v in pred_df["Success %"]]
    fig_bar.add_trace(go.Bar(
        x=pred_df["Command"],
        y=pred_df["Success %"],
        marker_color=colors,
        text=[f"{v:.0f}%" for v in pred_df["Success %"]],
        textposition="outside",
        textfont_size=12,
    ))
    fig_bar.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
        yaxis_range=[0, 110],
        yaxis_title="Success Probability %",
        xaxis_title="",
        margin=dict(l=40, r=20, t=20, b=60),
        height=300,
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    fig_bar.add_hline(y=75, line_dash="dot", line_color="rgba(0,210,106,0.3)", annotation_text="Safe", annotation_position="right")
    fig_bar.add_hline(y=40, line_dash="dot", line_color="rgba(255,184,0,0.3)", annotation_text="Risky", annotation_position="right")
    st.plotly_chart(fig_bar, use_container_width=True)

with col_table:
    st.dataframe(pred_df, use_container_width=True, hide_index=True, height=300)

st.divider()

# --- What-If Simulator ---
st.markdown("""
<div class="whatif-section">
    <h3 style="color: #B388FF; margin-top: 0;">🔮 What-If Simulator</h3>
    <p style="color: #8899A6; font-size: 0.85rem;">Compare predictions across multiple vehicles for the same command</p>
</div>
""", unsafe_allow_html=True)

whatif_cmd = st.selectbox("Command to Compare", COMMANDS, format_func=lambda x: x.replace("_", " ").title(), key="whatif_cmd")

if st.button("🔄 Run Comparison", key="whatif_run"):
    comparison_data = []
    for vin in vins:
        r = predict_command(vin, whatif_cmd)
        p = r.get("prediction", {})
        s = r.get("scores", {})
        a = r.get("recommended_action", {})
        prob = p.get("success_probability", 0)
        prob_pct = prob * 100 if isinstance(prob, (int, float)) and prob <= 1 else prob
        comparison_data.append({
            "VIN": vin,
            "Success %": round(prob_pct, 1),
            "Risk Level": p.get("risk_level", "N/A"),
            "Action": a.get("display_label", "N/A"),
            "Wait (min)": a.get("estimated_wait_minutes", 0),
            "Composite": s.get("composite_score", 0),
            "Risks": ", ".join(p.get("risk_factors", [])[:3]),
        })

    comp_df = pd.DataFrame(comparison_data)

    fig_comp = px.bar(
        comp_df, x="VIN", y="Success %",
        color="Success %",
        color_continuous_scale=["#FF4B4B", "#FFB800", "#00D26A"],
        range_color=[0, 100],
        text="Success %",
    )
    fig_comp.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
        yaxis_range=[0, 110],
        margin=dict(l=40, r=20, t=20, b=40),
        height=280,
        coloraxis_showscale=False,
    )
    fig_comp.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
    st.plotly_chart(fig_comp, use_container_width=True)
    st.dataframe(comp_df, use_container_width=True, hide_index=True)
