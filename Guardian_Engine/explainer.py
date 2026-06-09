"""
Explainer module — translates risk factors into customer-friendly messages.
Works with P1's models (VehicleState, ScoreBreakdown, Prediction).
Exports:
  - explain_prediction(prediction, state) → Explanation
  - explain_vehicle_status(state, scores) → Explanation
  - generate_explanation(risk_factors, composite) → API Explanation (for main.py)
"""

from models import VehicleState, ScoreBreakdown, Prediction, Explanation as P1Explanation, Severity
from api_models import Explanation as APIExplanation, SeverityLevel


# --- Explanation Templates ---
# priority: lower number = higher priority (shown first)

EXPLANATION_TEMPLATES = {
    "vehicle_offline": {
        "customer": "Your vehicle is currently offline. We'll notify you when it's reachable again.",
        "severity": "critical",
        "priority": 1,
    },
    "vehicle_likely_offline": {
        "customer": "Your vehicle appears to be unreachable. We'll try again when it reconnects.",
        "severity": "critical",
        "priority": 1,
    },
    "repeated_failures": {
        "customer": "Multiple commands have failed recently. We recommend checking vehicle connectivity or contacting support.",
        "severity": "critical",
        "priority": 1,
    },
    "vehicle_critical": {
        "customer": "Your vehicle needs immediate attention. Remote features are currently unavailable.",
        "severity": "critical",
        "priority": 1,
    },
    "command_will_fail": {
        "customer": "This command is unlikely to reach your vehicle right now. We can queue it and notify you when it's delivered.",
        "severity": "warning",
        "priority": 1,
    },
    "heartbeat_stale": {
        "customer": "Your vehicle hasn't connected recently. Commands may be delayed until it reconnects.",
        "severity": "warning",
        "priority": 2,
    },
    "tcu_flapping": {
        "customer": "Your vehicle's connection is unstable. We'll queue your command and deliver it when stable.",
        "severity": "warning",
        "priority": 2,
    },
    "connection_unstable": {
        "customer": "Your vehicle's connection is intermittent. Commands may take longer than usual.",
        "severity": "warning",
        "priority": 2,
    },
    "tcu_degraded": {
        "customer": "Your vehicle's communication unit is experiencing issues. Commands may be delayed.",
        "severity": "warning",
        "priority": 2,
    },
    "degrading_connection": {
        "customer": "Your vehicle's connectivity is declining. Remote features may become unavailable soon.",
        "severity": "warning",
        "priority": 2,
    },
    "signal_weak": {
        "customer": "Your vehicle has weak cellular signal. Remote features may be slower than usual.",
        "severity": "warning",
        "priority": 3,
    },
    "signal_degraded": {
        "customer": "Your vehicle's signal is weaker than normal. Minor delays possible.",
        "severity": "info",
        "priority": 4,
    },
    "tcu_overloaded": {
        "customer": "Your vehicle's system is under heavy load. Commands may take longer than usual.",
        "severity": "warning",
        "priority": 3,
    },
    "battery_low": {
        "customer": "Vehicle battery is low. Some remote features may be limited to preserve battery.",
        "severity": "warning",
        "priority": 3,
    },
    "battery_critical": {
        "customer": "Vehicle battery is critically low. Remote features may be unavailable.",
        "severity": "critical",
        "priority": 2,
    },
    "ota_in_motion": {
        "customer": "Software update cannot begin while driving. Park your vehicle to start the update.",
        "severity": "info",
        "priority": 3,
    },
    "ota_in_progress": {
        "customer": "A software update is in progress. Some features may be temporarily unavailable.",
        "severity": "info",
        "priority": 3,
    },
    "ota_download_incomplete": {
        "customer": "Software update is still downloading. Please wait for download to complete.",
        "severity": "info",
        "priority": 4,
    },
    "battery_low_ota": {
        "customer": "Software update is ready but waiting for sufficient battery. Charge above 50% to begin.",
        "severity": "info",
        "priority": 4,
    },
    "dtc_active": {
        "customer": "Your vehicle has reported a diagnostic issue. Some features may be affected.",
        "severity": "warning",
        "priority": 4,
    },
    "data_stale": {
        "customer": "Vehicle data is outdated. Current status may not be accurate.",
        "severity": "warning",
        "priority": 3,
    },
    "high_latency": {
        "customer": "Commands are taking longer than usual. Your vehicle may respond with a delay.",
        "severity": "info",
        "priority": 5,
    },
    "climate_needs_sustained_connection": {
        "customer": "Climate control requires a stable connection. Your vehicle's connection is weak — command may not complete.",
        "severity": "warning",
        "priority": 3,
    },
    "ota_no_wifi": {
        "customer": "Update download paused. Connect to Wi-Fi for faster download.",
        "severity": "info",
        "priority": 6,
    },
    "all_good": {
        "customer": "Your vehicle is connected and ready.",
        "severity": "good",
        "priority": 10,
    },
}


def _pick_best_template(risk_factors: list[str]) -> tuple[str, dict]:
    """Pick the highest-priority template matching the risk factors."""
    if not risk_factors:
        return "all_good", EXPLANATION_TEMPLATES["all_good"]

    matched = []
    for factor in risk_factors:
        if factor in EXPLANATION_TEMPLATES:
            t = EXPLANATION_TEMPLATES[factor]
            matched.append((t["priority"], factor, t))

    if not matched:
        return "unknown", {
            "customer": "Your vehicle may have limited connectivity. Some features may be affected.",
            "severity": "warning",
            "priority": 5,
        }

    matched.sort(key=lambda x: x[0])
    _, top_factor, top_template = matched[0]

    # If 2+ critical factors, escalate
    critical_count = sum(1 for _, _, t in matched if t["severity"] == "critical")
    if critical_count >= 2:
        return "multi_critical", {
            "customer": "Your vehicle has multiple critical issues. Please contact support for assistance.",
            "severity": "critical",
            "priority": 0,
        }

    return top_factor, top_template


# ──────────────────────────────────────────────
# P1 Interface (what their test_engine.py expects)
# ──────────────────────────────────────────────

def explain_prediction(prediction: Prediction, state: VehicleState) -> P1Explanation:
    """
    Called by P1's test: explain a command prediction.
    Returns P1's Explanation dataclass.
    """
    _, template = _pick_best_template(prediction.risk_factors)

    # Enhance message if command will likely fail
    if prediction.will_likely_fail and template["severity"] != "critical":
        message = f"{template['customer']} We'll queue your command and deliver it when conditions improve."
    else:
        message = template["customer"]

    tech = f"Command: {prediction.command} | Prob: {prediction.success_probability:.0%} | Risks: {', '.join(prediction.risk_factors)}"

    return P1Explanation(
        customer_message=message,
        factors=prediction.risk_factors,
        technical_details=tech,
        severity=Severity(template["severity"]),
    )


def explain_vehicle_status(state: VehicleState, scores: ScoreBreakdown) -> P1Explanation:
    """
    Called by P1's test: explain current vehicle status.
    Returns P1's Explanation dataclass.
    """
    _, template = _pick_best_template(scores.factors)
    tech = f"Composite: {scores.composite} | Reachability: {scores.reachability} | Cmd Prob: {scores.command_probability:.2f}"

    # Override for extreme composite
    if scores.composite < 20:
        return P1Explanation(
            customer_message="Your vehicle needs attention. Remote features are currently unavailable.",
            factors=scores.factors,
            technical_details=tech,
            severity=Severity.CRITICAL,
        )

    if scores.composite >= 85 and not scores.factors:
        return P1Explanation(
            customer_message="Your vehicle is connected and all systems are running smoothly.",
            factors=[],
            technical_details=tech,
            severity=Severity.GOOD,
        )

    return P1Explanation(
        customer_message=template["customer"],
        factors=scores.factors,
        technical_details=tech,
        severity=Severity(template["severity"]),
    )


# ──────────────────────────────────────────────
# API Interface (what our main.py uses)
# ──────────────────────────────────────────────

def generate_explanation(risk_factors: list[str], scores: ScoreBreakdown) -> APIExplanation:
    """
    For API responses: converts risk factors + P1 scores into a full APIExplanation
    with customer_message, severity, and technical_details.
    """
    _, template = _pick_best_template(risk_factors)

    if not risk_factors:
        return APIExplanation(
            customer_message=template["customer"],
            severity=SeverityLevel.good,
            technical_details=f"Composite: {scores.composite}/100 — All systems nominal",
        )

    severity = SeverityLevel(template["severity"])

    # Build technical details
    tech_parts = [f.replace("_", " ").title() for f in risk_factors]
    technical_details = (
        f"Active risks: {', '.join(tech_parts)} | "
        f"Composite: {scores.composite} | "
        f"Reachability: {scores.reachability} | "
        f"Cmd Prob: {scores.command_probability:.2f}"
    )

    return APIExplanation(
        customer_message=template["customer"],
        severity=severity,
        technical_details=technical_details,
    )


def get_status_explanation(risk_factors: list[str], scores: ScoreBreakdown) -> APIExplanation:
    """
    For API vehicle status display: adds composite-score overrides.
    """
    explanation = generate_explanation(risk_factors, scores)

    if scores.composite < 20:
        return APIExplanation(
            customer_message="Your vehicle needs attention. Remote features are currently unavailable.",
            severity=SeverityLevel.critical,
            technical_details=explanation.technical_details,
        )

    if scores.composite >= 85 and not risk_factors:
        return APIExplanation(
            customer_message="Your vehicle is connected and all systems are running smoothly.",
            severity=SeverityLevel.good,
            technical_details=f"Composite: {scores.composite}/100 — Excellent",
        )

    return explanation
