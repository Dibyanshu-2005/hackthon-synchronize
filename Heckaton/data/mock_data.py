"""
Mock data layer matching the engine team's API schema exactly.
Replace function bodies with real HTTP calls when integrating.

Endpoints modeled:
  1. /vehicles/{vin}/predict/{command}
  2. /vehicles/{vin}
  3. /vehicles/{vin}/explain
  4. /vehicles
  5. /fleet/at-risk
"""

import random
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd


# --- Constants ---

COMMANDS = [
    "remote_lock",
    "remote_unlock",
    "remote_climate_start",
    "remote_climate_stop",
    "vehicle_status_refresh",
    "ota_update",
    "diagnostics_request",
    "horn_and_lights",
]

RISK_FACTORS = [
    "heartbeat_stale",
    "signal_weak",
    "tcu_flapping",
    "high_latency",
    "battery_low",
    "ecu_unresponsive",
    "network_congestion",
    "device_twin_stale",
    "command_timeout_history",
    "ota_blocked",
    "region_service_degraded",
]

ACTIONS = [
    "execute_immediately",
    "queue_and_notify",
    "retry_with_backoff",
    "send_wakeup_ping",
    "escalate_to_support",
    "notify_customer_delay",
    "suggest_alternative",
]

ACTION_LABELS = {
    "execute_immediately": "Execute Now",
    "queue_and_notify": "Queue & Notify Me",
    "retry_with_backoff": "Retry Automatically",
    "send_wakeup_ping": "Wake Up Vehicle",
    "escalate_to_support": "Contact Support",
    "notify_customer_delay": "Notify of Delay",
    "suggest_alternative": "Try Alternative",
}

SEVERITIES = ["info", "warning", "critical"]

VEHICLE_PROFILES = {
    "VIN_A_001": {
        "model": "Model-S",
        "region": "IN-North",
        "composite": 92, "connectivity": 90, "ecu_health": 95, "cmd_history": 88, "vehicle_health": 94,
        "status": "healthy",
        "risk_factors": [],
    },
    "VIN_A_002": {
        "model": "Model-X",
        "region": "IN-West",
        "composite": 88, "connectivity": 85, "ecu_health": 90, "cmd_history": 86, "vehicle_health": 91,
        "status": "healthy",
        "risk_factors": [],
    },
    "VIN_B_001": {
        "model": "Model-R",
        "region": "IN-East",
        "composite": 55, "connectivity": 48, "ecu_health": 60, "cmd_history": 50, "vehicle_health": 68,
        "status": "warning",
        "risk_factors": ["signal_weak", "high_latency"],
    },
    "VIN_B_002": {
        "model": "Model-X",
        "region": "IN-South",
        "composite": 48, "connectivity": 30, "ecu_health": 55, "cmd_history": 52, "vehicle_health": 76,
        "status": "warning",
        "risk_factors": ["heartbeat_stale", "signal_weak", "tcu_flapping"],
    },
    "VIN_C_001": {
        "model": "Model-C",
        "region": "IN-North",
        "composite": 25, "connectivity": 15, "ecu_health": 30, "cmd_history": 20, "vehicle_health": 40,
        "status": "critical",
        "risk_factors": ["heartbeat_stale", "ecu_unresponsive", "tcu_flapping", "command_timeout_history"],
    },
    "VIN_C_002": {
        "model": "Model-S",
        "region": "IN-South",
        "composite": 35, "connectivity": 25, "ecu_health": 40, "cmd_history": 35, "vehicle_health": 50,
        "status": "critical",
        "risk_factors": ["network_congestion", "device_twin_stale", "battery_low"],
    },
    "VIN_D_001": {
        "model": "Model-R",
        "region": "IN-West",
        "composite": 62, "connectivity": 58, "ecu_health": 65, "cmd_history": 60, "vehicle_health": 70,
        "status": "warning",
        "risk_factors": ["high_latency", "command_timeout_history"],
    },
    "VIN_D_002": {
        "model": "Model-C",
        "region": "IN-East",
        "composite": 85, "connectivity": 82, "ecu_health": 88, "cmd_history": 84, "vehicle_health": 87,
        "status": "healthy",
        "risk_factors": [],
    },
}

CUSTOMER_MESSAGES = {
    "healthy": "All systems operational. Your vehicle is ready for remote commands.",
    "warning": "Your vehicle's connectivity is declining. Remote features may become unavailable soon.",
    "critical": "Your vehicle hasn't connected recently. Commands may be delayed until it reconnects.",
}

TECHNICAL_DETAILS_TEMPLATES = {
    "heartbeat_stale": "Last heartbeat: {minutes} min ago",
    "signal_weak": "Signal: {pct}%",
    "tcu_flapping": "Reconnects: {count} in 15 min | TCU: degraded",
    "high_latency": "Avg latency: {ms}ms (threshold: 500ms)",
    "battery_low": "Battery: {pct}%",
    "ecu_unresponsive": "ECU response: timeout after {ms}ms",
    "network_congestion": "Network load: {pct}% capacity",
    "device_twin_stale": "Device twin last synced: {minutes} min ago",
    "command_timeout_history": "Last {count} commands: {timeout_count} timeouts",
    "ota_blocked": "OTA pending: blocked by {reason}",
    "region_service_degraded": "Region health: degraded ({pct}% normal throughput)",
}


def _jitter(base, variance=5):
    return max(0, min(100, base + random.uniform(-variance, variance)))


def _generate_technical_details(risk_factors):
    parts = []
    for rf in risk_factors:
        template = TECHNICAL_DETAILS_TEMPLATES.get(rf, rf)
        formatted = template.format(
            minutes=random.randint(20, 90),
            pct=random.randint(15, 45),
            count=random.randint(4, 12),
            ms=random.randint(600, 3000),
            timeout_count=random.randint(2, 6),
            reason="low battery" if rf == "ota_blocked" else "connectivity",
        )
        parts.append(formatted)
    return " | ".join(parts)


# --- Endpoint 1: /vehicles/{vin}/predict/{command} ---

def predict_command(vin: str, command: str) -> dict:
    profile = VEHICLE_PROFILES.get(vin)
    if not profile:
        return {"error": "Vehicle not found"}

    base_prob = profile["composite"] / 100.0
    command_modifier = random.uniform(-0.15, 0.05)
    success_prob = max(0.05, min(0.99, base_prob + command_modifier))

    risk_factors = profile["risk_factors"][:]
    if success_prob < 0.5 and random.random() > 0.5:
        extra = random.choice([rf for rf in RISK_FACTORS if rf not in risk_factors])
        risk_factors.append(extra)

    is_degrading = profile["status"] in ["warning", "critical"] and random.random() > 0.3
    confidence = round(random.uniform(0.7, 0.95), 2)

    if success_prob > 0.75:
        action = "execute_immediately"
        wait = 0
        fallback = None
    elif success_prob > 0.5:
        action = random.choice(["retry_with_backoff", "send_wakeup_ping"])
        wait = random.randint(3, 10)
        fallback = "queue_and_notify"
    else:
        action = "queue_and_notify"
        wait = random.randint(10, 30)
        fallback = "escalate_to_support"

    severity = "info" if success_prob > 0.75 else "warning" if success_prob > 0.4 else "critical"

    return {
        "vin": vin,
        "command": command,
        "timestamp": datetime.now().isoformat() + "Z",
        "prediction": {
            "success_probability": round(success_prob, 2),
            "risk_factors": risk_factors,
            "is_degrading": is_degrading,
            "confidence": confidence,
        },
        "scores": {
            "composite_score": round(_jitter(profile["composite"], 2), 1),
            "connectivity_score": round(_jitter(profile["connectivity"], 3), 1),
            "ecu_health_score": round(_jitter(profile["ecu_health"], 2), 1),
            "command_history_score": round(_jitter(profile["cmd_history"], 3), 1),
            "vehicle_health_score": round(_jitter(profile["vehicle_health"], 2), 1),
        },
        "explanation": {
            "customer_message": CUSTOMER_MESSAGES.get(severity, CUSTOMER_MESSAGES["warning"]),
            "severity": severity,
            "technical_details": _generate_technical_details(risk_factors) if risk_factors else "All systems nominal",
        },
        "recommended_action": {
            "action": action,
            "display_label": ACTION_LABELS[action],
            "reason": f"Success probability {int(success_prob*100)}% — {'safe for direct execution' if action == 'execute_immediately' else 'too low for direct execution'}",
            "estimated_wait_minutes": wait,
            "fallback_action": fallback,
            "details": {
                "retry_count": 0,
                "notify_on_delivery": True,
            },
        },
    }


# --- Endpoint 2: /vehicles/{vin} ---

def get_vehicle_detail(vin: str) -> dict:
    profile = VEHICLE_PROFILES.get(vin)
    if not profile:
        return {"error": "Vehicle not found"}

    severity = "info" if profile["status"] == "healthy" else profile["status"]
    if severity == "healthy":
        severity = "info"

    return {
        "vin": vin,
        "model": profile["model"],
        "region": profile["region"],
        "scores": {
            "composite_score": round(_jitter(profile["composite"], 2), 1),
            "connectivity_score": round(_jitter(profile["connectivity"], 3), 1),
            "ecu_health_score": round(_jitter(profile["ecu_health"], 2), 1),
            "command_history_score": round(_jitter(profile["cmd_history"], 3), 1),
            "vehicle_health_score": round(_jitter(profile["vehicle_health"], 2), 1),
        },
        "status": {
            "overall": profile["status"],
            "customer_message": CUSTOMER_MESSAGES.get(profile["status"], CUSTOMER_MESSAGES["warning"]),
            "severity": severity,
        },
        "risk_factors": profile["risk_factors"],
        "raw_payload": {"heartbeat_interval_ms": random.randint(1000, 60000), "signal_strength_pct": random.randint(10, 95)},
        "updated_at": datetime.now().isoformat() + "Z",
    }


# --- Endpoint 3: /vehicles/{vin}/explain ---

def get_vehicle_explanation(vin: str) -> dict:
    profile = VEHICLE_PROFILES.get(vin)
    if not profile:
        return {"error": "Vehicle not found"}

    severity = "info" if profile["status"] == "healthy" else profile["status"]
    if severity == "healthy":
        severity = "info"

    return {
        "vin": vin,
        "customer_message": CUSTOMER_MESSAGES.get(profile["status"], CUSTOMER_MESSAGES["warning"]),
        "severity": severity,
        "technical_details": _generate_technical_details(profile["risk_factors"]) if profile["risk_factors"] else "All systems nominal",
        "risk_factors": profile["risk_factors"],
        "timestamp": datetime.now().isoformat() + "Z",
    }


# --- Endpoint 4: /vehicles ---

def get_all_vehicles() -> dict:
    vehicles = []
    for vin, profile in VEHICLE_PROFILES.items():
        vehicles.append({
            "vin": vin,
            "model": profile["model"],
            "composite_score": round(_jitter(profile["composite"], 2), 1),
            "status": profile["status"],
            "risk_factor_count": len(profile["risk_factors"]),
            "top_risk": profile["risk_factors"][0] if profile["risk_factors"] else None,
        })
    return {"vehicles": vehicles, "total": len(vehicles)}


# --- Endpoint 5: /fleet/at-risk ---

def get_fleet_at_risk(threshold: float = 60.0) -> dict:
    at_risk = []
    for vin, profile in VEHICLE_PROFILES.items():
        score = round(_jitter(profile["composite"], 2), 1)
        if score < threshold:
            severity = "critical" if score < 35 else "warning"
            at_risk.append({
                "vin": vin,
                "composite_score": score,
                "severity": severity,
                "top_risk": profile["risk_factors"][0] if profile["risk_factors"] else None,
            })
    return {
        "threshold": threshold,
        "at_risk_count": len(at_risk),
        "vehicles": sorted(at_risk, key=lambda x: x["composite_score"]),
    }


# --- Helper functions for dashboard (derived from endpoints above) ---

def get_fleet_dataframe() -> pd.DataFrame:
    """Get all vehicles as a DataFrame for table/chart display."""
    rows = []
    for vin, profile in VEHICLE_PROFILES.items():
        rows.append({
            "vin": vin,
            "model": profile["model"],
            "region": profile["region"],
            "status": profile["status"],
            "composite_score": round(_jitter(profile["composite"], 2), 1),
            "connectivity_score": round(_jitter(profile["connectivity"], 3), 1),
            "ecu_health_score": round(_jitter(profile["ecu_health"], 2), 1),
            "command_history_score": round(_jitter(profile["cmd_history"], 3), 1),
            "vehicle_health_score": round(_jitter(profile["vehicle_health"], 2), 1),
            "risk_factor_count": len(profile["risk_factors"]),
            "top_risk": profile["risk_factors"][0] if profile["risk_factors"] else "none",
            "risk_factors": profile["risk_factors"],
            "is_degrading": profile["status"] in ["warning", "critical"],
        })
    return pd.DataFrame(rows)


def get_all_predictions() -> pd.DataFrame:
    """Get predictions for every vehicle x command combination."""
    rows = []
    for vin in VEHICLE_PROFILES:
        for command in COMMANDS:
            pred = predict_command(vin, command)
            rows.append({
                "vin": vin,
                "command": command,
                "success_probability": pred["prediction"]["success_probability"],
                "risk_factors": pred["prediction"]["risk_factors"],
                "is_degrading": pred["prediction"]["is_degrading"],
                "confidence": pred["prediction"]["confidence"],
                "composite_score": pred["scores"]["composite_score"],
                "connectivity_score": pred["scores"]["connectivity_score"],
                "ecu_health_score": pred["scores"]["ecu_health_score"],
                "command_history_score": pred["scores"]["command_history_score"],
                "vehicle_health_score": pred["scores"]["vehicle_health_score"],
                "severity": pred["explanation"]["severity"],
                "customer_message": pred["explanation"]["customer_message"],
                "technical_details": pred["explanation"]["technical_details"],
                "recommended_action": pred["recommended_action"]["action"],
                "action_label": pred["recommended_action"]["display_label"],
                "action_reason": pred["recommended_action"]["reason"],
                "estimated_wait_minutes": pred["recommended_action"]["estimated_wait_minutes"],
                "fallback_action": pred["recommended_action"]["fallback_action"],
            })
    return pd.DataFrame(rows)


def get_command_history(hours: int = 48) -> pd.DataFrame:
    """Simulated command execution history for analytics."""
    history = []
    now = datetime.now()

    for _ in range(300):
        vin = random.choice(list(VEHICLE_PROFILES.keys()))
        profile = VEHICLE_PROFILES[vin]
        command = random.choice(COMMANDS)
        timestamp = now - timedelta(hours=random.uniform(0, hours))

        base_success = profile["composite"] / 100.0
        success = random.random() < base_success
        latency = random.uniform(0.3, 2.5) if profile["status"] == "healthy" else random.uniform(2.0, 15.0)

        risk_factors = profile["risk_factors"] if not success else []
        failure_reason = risk_factors[0] if risk_factors else None

        history.append({
            "vin": vin,
            "command": command,
            "timestamp": timestamp,
            "success": success,
            "latency_seconds": round(latency, 2),
            "failure_reason": failure_reason,
            "model": profile["model"],
            "region": profile["region"],
        })

    return pd.DataFrame(history).sort_values("timestamp", ascending=False).reset_index(drop=True)


def get_alerts() -> pd.DataFrame:
    """Active alerts derived from at-risk vehicles and predictions."""
    alerts = []
    now = datetime.now()

    for vin, profile in VEHICLE_PROFILES.items():
        if profile["status"] == "healthy":
            continue

        explanation = get_vehicle_explanation(vin)
        severity = "critical" if profile["composite"] < 35 else "warning"

        alerts.append({
            "vin": vin,
            "model": profile["model"],
            "severity": severity,
            "status": profile["status"],
            "customer_message": explanation["customer_message"],
            "technical_details": explanation["technical_details"],
            "risk_factors": explanation["risk_factors"],
            "top_risk": explanation["risk_factors"][0] if explanation["risk_factors"] else None,
            "recommended_action": random.choice(ACTIONS[1:]),
            "action_label": ACTION_LABELS[random.choice(ACTIONS[1:])],
            "timestamp": now - timedelta(minutes=random.randint(2, 45)),
            "is_degrading": True,
            "composite_score": profile["composite"],
        })

    return pd.DataFrame(alerts).sort_values("timestamp", ascending=False).reset_index(drop=True)
