"""
Mock data layer — realistic production fleet simulation.
Models a Mercedes-like connected vehicle fleet where MOST vehicles are healthy
and the Guardian catches the rare edge cases before they become customer failures.

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


# --- Commands (Mercedes-me style) ---

COMMANDS = [
    "door_lock",
    "door_unlock",
    "climate_start",
    "climate_stop",
    "vehicle_status",
    "engine_start",
    "ota_update",
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

# --- REALISTIC fleet: Most vehicles are healthy, 1-2 edge cases ---

VEHICLE_PROFILES = {
    "WDD2130421A123456": {
        "model": "C-Class W206",
        "region": "IN-North",
        "composite": 96, "connectivity": 98, "ecu_health": 97, "cmd_history": 95, "vehicle_health": 96,
        "status": "healthy",
        "risk_factors": [],
    },
    "WDD2230461A789012": {
        "model": "E-Class W214",
        "region": "IN-West",
        "composite": 94, "connectivity": 96, "ecu_health": 95, "cmd_history": 92, "vehicle_health": 94,
        "status": "healthy",
        "risk_factors": [],
    },
    "WDD1673021A345678": {
        "model": "GLC X254",
        "region": "IN-South",
        "composite": 93, "connectivity": 95, "ecu_health": 94, "cmd_history": 91, "vehicle_health": 93,
        "status": "healthy",
        "risk_factors": [],
    },
    "WDD2532171A456789": {
        "model": "GLE W167",
        "region": "IN-East",
        "composite": 91, "connectivity": 93, "ecu_health": 92, "cmd_history": 89, "vehicle_health": 91,
        "status": "healthy",
        "risk_factors": [],
    },
    "WDD2470321A567890": {
        "model": "S-Class W223",
        "region": "IN-North",
        "composite": 97, "connectivity": 99, "ecu_health": 98, "cmd_history": 96, "vehicle_health": 97,
        "status": "healthy",
        "risk_factors": [],
    },
    "WDD1770041A678901": {
        "model": "GLA H247",
        "region": "IN-West",
        "composite": 68, "connectivity": 58, "ecu_health": 72, "cmd_history": 65, "vehicle_health": 80,
        "status": "warning",
        "risk_factors": ["signal_weak", "high_latency", "device_twin_stale"],
    },
    "WDD2060421A890123": {
        "model": "A-Class W177",
        "region": "IN-South",
        "composite": 34, "connectivity": 18, "ecu_health": 42, "cmd_history": 30, "vehicle_health": 55,
        "status": "critical",
        "risk_factors": ["heartbeat_stale", "tcu_flapping", "ecu_unresponsive", "command_timeout_history"],
    },
}

CUSTOMER_MESSAGES = {
    "healthy": "All systems operational. Your vehicle is ready for remote commands.",
    "warning": "Your vehicle's connectivity is weakening. Remote features may experience delays.",
    "critical": "Your vehicle hasn't connected recently. Commands will be queued and delivered when connectivity is restored.",
}

TECHNICAL_DETAILS_TEMPLATES = {
    "heartbeat_stale": "Last heartbeat: {minutes} min ago (threshold: 2 min)",
    "signal_weak": "Signal: {pct}% (threshold: 40%)",
    "tcu_flapping": "TCU reconnects: {count} in 15 min (threshold: 3)",
    "high_latency": "Avg latency: {ms}ms (threshold: 500ms)",
    "battery_low": "12V battery: {pct}% (threshold: 30%)",
    "ecu_unresponsive": "ECU response: timeout after {ms}ms",
    "network_congestion": "Network load: {pct}% capacity",
    "device_twin_stale": "Device twin last synced: {minutes} min ago",
    "command_timeout_history": "Last {count} commands: {timeout_count} timeouts",
    "ota_blocked": "OTA pending: blocked by {reason}",
    "region_service_degraded": "Region health: degraded ({pct}% normal throughput)",
}


def _jitter(base, variance=2):
    return max(0, min(100, base + random.uniform(-variance, variance)))


def _generate_technical_details(risk_factors):
    parts = []
    for rf in risk_factors:
        template = TECHNICAL_DETAILS_TEMPLATES.get(rf, rf)
        formatted = template.format(
            minutes=random.randint(20, 90),
            pct=random.randint(12, 35),
            count=random.randint(5, 12),
            ms=random.randint(800, 4000),
            timeout_count=random.randint(2, 5),
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

    # Healthy cars: commands almost always succeed (95-99%)
    if profile["status"] == "healthy":
        success_prob = max(0.92, min(0.99, base_prob + random.uniform(-0.03, 0.02)))
    elif profile["status"] == "warning":
        success_prob = max(0.45, min(0.78, base_prob + random.uniform(-0.10, 0.05)))
    else:
        success_prob = max(0.08, min(0.35, base_prob * 0.6 + random.uniform(-0.10, 0.05)))

    # Climate/engine start needs sustained connection — slightly lower for degraded vehicles
    if command in ("climate_start", "engine_start") and profile["status"] != "healthy":
        success_prob *= 0.85

    risk_factors = profile["risk_factors"][:]
    is_degrading = profile["status"] == "critical" or (profile["status"] == "warning" and random.random() > 0.5)
    confidence = round(random.uniform(0.82, 0.96), 2)

    if success_prob > 0.85:
        action = "execute_immediately"
        wait = 0
        fallback = None
    elif success_prob > 0.55:
        action = random.choice(["retry_with_backoff", "send_wakeup_ping"])
        wait = random.randint(2, 8)
        fallback = "queue_and_notify"
    else:
        action = "queue_and_notify"
        wait = random.randint(10, 30)
        fallback = "escalate_to_support"

    severity = "info" if success_prob > 0.85 else "warning" if success_prob > 0.45 else "critical"

    return {
        "vin": vin,
        "command": command,
        "timestamp": datetime.now().isoformat() + "Z",
        "prediction": {
            "success_probability": round(success_prob, 3),
            "risk_factors": risk_factors,
            "is_degrading": is_degrading,
            "confidence": confidence,
        },
        "scores": {
            "composite_score": round(_jitter(profile["composite"], 1), 1),
            "connectivity_score": round(_jitter(profile["connectivity"], 2), 1),
            "ecu_health_score": round(_jitter(profile["ecu_health"], 1), 1),
            "command_history_score": round(_jitter(profile["cmd_history"], 2), 1),
            "vehicle_health_score": round(_jitter(profile["vehicle_health"], 1), 1),
        },
        "explanation": {
            "customer_message": CUSTOMER_MESSAGES.get(severity if severity != "info" else "healthy", CUSTOMER_MESSAGES["healthy"]),
            "severity": severity,
            "technical_details": _generate_technical_details(risk_factors) if risk_factors else "All systems nominal",
        },
        "recommended_action": {
            "action": action,
            "display_label": ACTION_LABELS[action],
            "reason": f"Success probability {int(success_prob*100)}% — {'safe for immediate execution' if action == 'execute_immediately' else 'queuing for optimal delivery'}",
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
            "composite_score": round(_jitter(profile["composite"], 1), 1),
            "connectivity_score": round(_jitter(profile["connectivity"], 2), 1),
            "ecu_health_score": round(_jitter(profile["ecu_health"], 1), 1),
            "command_history_score": round(_jitter(profile["cmd_history"], 2), 1),
            "vehicle_health_score": round(_jitter(profile["vehicle_health"], 1), 1),
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
            "composite_score": round(_jitter(profile["composite"], 1), 1),
            "status": profile["status"],
            "risk_factor_count": len(profile["risk_factors"]),
            "top_risk": profile["risk_factors"][0] if profile["risk_factors"] else None,
        })
    return {"vehicles": vehicles, "total": len(vehicles)}


# --- Endpoint 5: /fleet/at-risk ---

def get_fleet_at_risk(threshold: float = 75.0) -> dict:
    at_risk = []
    for vin, profile in VEHICLE_PROFILES.items():
        score = round(_jitter(profile["composite"], 1), 1)
        if score < threshold:
            severity = "critical" if score < 40 else "warning"
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


# --- Helper functions for dashboard ---

def get_fleet_dataframe() -> pd.DataFrame:
    rows = []
    for vin, profile in VEHICLE_PROFILES.items():
        rows.append({
            "vin": vin,
            "model": profile["model"],
            "region": profile["region"],
            "status": profile["status"],
            "composite_score": round(_jitter(profile["composite"], 1), 1),
            "connectivity_score": round(_jitter(profile["connectivity"], 2), 1),
            "ecu_health_score": round(_jitter(profile["ecu_health"], 1), 1),
            "command_history_score": round(_jitter(profile["cmd_history"], 2), 1),
            "vehicle_health_score": round(_jitter(profile["vehicle_health"], 1), 1),
            "risk_factor_count": len(profile["risk_factors"]),
            "top_risk": profile["risk_factors"][0] if profile["risk_factors"] else "none",
            "risk_factors": profile["risk_factors"],
            "is_degrading": profile["status"] in ["warning", "critical"],
        })
    return pd.DataFrame(rows)


def get_all_predictions() -> pd.DataFrame:
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
    history = []
    now = datetime.now()

    for _ in range(400):
        vin = random.choice(list(VEHICLE_PROFILES.keys()))
        profile = VEHICLE_PROFILES[vin]
        command = random.choice(COMMANDS)
        timestamp = now - timedelta(hours=random.uniform(0, hours))

        # Realistic: healthy cars succeed 96%+, warning 70%, critical 30%
        if profile["status"] == "healthy":
            success = random.random() < 0.97
            latency = random.uniform(0.3, 1.8)
        elif profile["status"] == "warning":
            success = random.random() < 0.70
            latency = random.uniform(1.5, 6.0)
        else:
            success = random.random() < 0.30
            latency = random.uniform(4.0, 15.0)

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
    alerts = []
    now = datetime.now()

    for vin, profile in VEHICLE_PROFILES.items():
        if profile["status"] == "healthy":
            continue

        explanation = get_vehicle_explanation(vin)
        severity = "critical" if profile["composite"] < 40 else "warning"

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
