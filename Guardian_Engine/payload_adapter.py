"""Adapts the incoming vehicle payload into scoring inputs."""

from datetime import datetime
from models import VehicleState, ConnectionStatus


def _signal_percent_to_dbm(percent: int) -> float:
    """Convert signal strength percentage (0-100) to dBm (-120 to -50)."""
    return -120 + (percent / 100) * 70


def _connection_state_map(state: str) -> ConnectionStatus:
    mapping = {
        "connected": ConnectionStatus.CONNECTED,
        "stable": ConnectionStatus.CONNECTED,
        "unstable": ConnectionStatus.INTERMITTENT,
        "intermittent": ConnectionStatus.INTERMITTENT,
        "disconnected": ConnectionStatus.OFFLINE,
        "offline": ConnectionStatus.OFFLINE,
    }
    return mapping.get(state.lower(), ConnectionStatus.INTERMITTENT)


def payload_to_vehicle_state(payload: dict) -> VehicleState:
    """Convert raw vehicle payload JSON to VehicleState for scoring."""

    conn = payload.get("connectivity", {})
    ecu = payload.get("ecuHealth", {})
    cmd = payload.get("commandLifecycle", {})
    battery = payload.get("batteryCharging", {})
    ota = payload.get("ota", {})
    driving = payload.get("drivingState", {})
    location = payload.get("locationTrip", {})

    # Heartbeat: use the worse of connectivity.lastHeartbeatMinutes and ecuHealth.lastEcuHeartbeatAgeSeconds
    heartbeat_from_conn = conn.get("lastHeartbeatMinutes", 0) * 60
    heartbeat_from_ecu = ecu.get("lastEcuHeartbeatAgeSeconds", 0)
    heartbeat_age = max(heartbeat_from_conn, heartbeat_from_ecu)

    # Signal strength: convert percent to dBm
    signal_dbm = _signal_percent_to_dbm(conn.get("signalStrengthPercent", 50))

    # Reconnect count: payload gives 15-min window, scale to 1h estimate
    reconnects_15m = conn.get("reconnectCountLast15Min", 0)
    reconnects_1h = reconnects_15m * 4

    # Command history
    failed_24h = cmd.get("failedCommandsLast24h", 0)
    delayed_24h = cmd.get("delayedCommandsLast24h", 0)
    # Estimate hourly from 24h data
    commands_attempted = max(1, (failed_24h + delayed_24h + 5))  # assume at least 5 successful
    commands_succeeded = max(0, commands_attempted - failed_24h)

    # ACK latency
    ack_latency = cmd.get("lastCommandLatencyMs", 500)

    # OTA state
    ota_available = ota.get("otaPackageAvailable", False)
    ota_downloaded = ota.get("otaStatus", "") in ("downloaded", "ready", "pending_install")

    # Is parked
    is_parked = driving.get("drivingMode", "").lower() in ("parked", "park", "standby")

    # Location freshness — if GPS not available, estimate from device twin age
    if location.get("gpsAvailable", True):
        loc_fresh = 30
    else:
        loc_fresh = conn.get("deviceTwinAgeMinutes", 5) * 60

    return VehicleState(
        vin=payload.get("vin", "UNKNOWN"),
        name=f"Vehicle {payload.get('vin', 'X')}",
        model=payload.get("model", "Unknown"),
        timestamp=datetime.now(),
        heartbeat_age_seconds=int(heartbeat_age),
        signal_strength_dbm=signal_dbm,
        network_type=conn.get("networkType", "4G"),
        tcu_reconnect_count_1h=reconnects_1h,
        connection_status=_connection_state_map(conn.get("connectionState", "connected")),
        last_ack_latency_ms=ack_latency,
        commands_attempted_1h=commands_attempted,
        commands_succeeded_1h=commands_succeeded,
        last_command_type=cmd.get("lastCommandType", None),
        last_command_status=cmd.get("lastCommandStatus", None),
        ota_package_available=ota_available,
        ota_package_downloaded=ota_downloaded,
        ota_blocker=payload.get("ota", {}).get("otaErrorCodes", [None])[0] if payload.get("ota", {}).get("otaErrorCodes") else None,
        battery_level=battery.get("batteryLevel", 80),
        is_parked=is_parked,
        is_charging=battery.get("chargingStatus", "not_charging") != "not_charging",
        location_freshness_seconds=loc_fresh,
    )


def extract_enhanced_signals(payload: dict) -> dict:
    """Extract additional signals beyond VehicleState for richer scoring context."""

    ecu = payload.get("ecuHealth", {})
    diag = payload.get("diagnostics", {})
    cloud = payload.get("cloudServiceMetrics", {})
    dq = payload.get("dataQuality", {})
    app = payload.get("mobileApp", {})
    sw = payload.get("softwareInventory", {})
    failures = payload.get("failureReasons", [])
    vh = payload.get("vehicleHealth", {})

    return {
        # ECU Health
        "ecu_status": ecu.get("primaryEcuStatus", "normal"),
        "tcu_cpu_percent": ecu.get("tcuCpuUsagePercent", 0),
        "tcu_memory_percent": ecu.get("tcuMemoryUsagePercent", 0),

        # Diagnostics
        "active_dtc_count": diag.get("activeDtcCount", 0),
        "highest_dtc_severity": diag.get("highestDtcSeverity", "none"),
        "dtc_codes": diag.get("dtcCodes", []),

        # Cloud path health
        "ingestion_latency_ms": cloud.get("ingestionLatencyMs", 0),
        "processing_latency_ms": cloud.get("processingLatencyMs", 0),
        "message_loss_percent": cloud.get("messageLossRatePercent", 0),
        "cloud_health": cloud.get("serviceHealth", "healthy"),

        # Data quality
        "data_completeness": dq.get("completeness", 1.0),
        "data_accuracy": dq.get("accuracy", 1.0),
        "anomaly_count": dq.get("anomalyCount", 0),

        # App interaction
        "failed_app_attempts_24h": app.get("failedAppAttemptsLast24h", 0),
        "repeated_attempts": app.get("repeatedFeatureAttempts", 0),

        # Software
        "outdated_components": sw.get("componentsOutdatedCount", 0),
        "critical_outdated": sw.get("criticalComponentsOutdated", []),

        # Vehicle health (already scored by vehicle)
        "vehicle_health_score": vh.get("vehicleHealthScore", 100),
        "vehicle_overall_status": vh.get("overallStatus", "normal"),

        # Failure reasons
        "failure_reasons": failures,
    }
