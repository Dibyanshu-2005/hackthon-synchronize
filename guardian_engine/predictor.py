from models import VehicleState, Prediction, RiskLevel


COMMAND_BASE_WEIGHT = {
    "remote_lock": 0.98,
    "remote_unlock": 0.98,
    "remote_climate": 0.92,
    "remote_horn": 0.96,
    "status_refresh": 0.95,
    "ota_install": 0.70,
}

COMMAND_BASE_LATENCY = {
    "remote_lock": 800,
    "remote_unlock": 800,
    "remote_climate": 3500,
    "remote_horn": 1200,
    "status_refresh": 2000,
    "ota_install": None,
}


def predict_command_probability(state: VehicleState, command: str) -> float:
    command = command.lower().replace(" ", "_")
    base_weight = COMMAND_BASE_WEIGHT.get(command, 0.80)

    # Heartbeat freshness factor
    hb = state.heartbeat_age_seconds
    if hb <= 30:
        f_hb = 1.0
    elif hb <= 120:
        f_hb = 1.0 - (hb - 30) * 0.0017
    elif hb <= 300:
        f_hb = 0.85 - (hb - 120) * 0.0017
    elif hb <= 600:
        f_hb = 0.55 - (hb - 300) * 0.001
    else:
        f_hb = max(0.02, 0.25 - (hb - 600) * 0.0005)

    # Signal strength factor
    sig = state.signal_strength_dbm
    if sig >= -65:
        f_sig = 1.0
    elif sig >= -85:
        f_sig = 1.0 - (abs(sig) - 65) * 0.0075
    elif sig >= -100:
        f_sig = 0.85 - (abs(sig) - 85) * 0.02
    elif sig >= -110:
        f_sig = 0.55 - (abs(sig) - 100) * 0.03
    else:
        f_sig = max(0.02, 0.25 - (abs(sig) - 110) * 0.02)

    # Connection stability factor
    rc = state.tcu_reconnect_count_1h
    if rc == 0:
        f_stab = 1.0
    elif rc <= 3:
        f_stab = 1.0 - rc * 0.067
    elif rc <= 7:
        f_stab = 0.80 - (rc - 3) * 0.075
    elif rc <= 12:
        f_stab = 0.50 - (rc - 7) * 0.05
    else:
        f_stab = max(0.05, 0.25 - (rc - 12) * 0.05)

    # Historical success rate
    if state.commands_attempted_1h > 0:
        f_hist = state.commands_succeeded_1h / state.commands_attempted_1h
    else:
        f_hist = 0.85

    # Connection status — applied as post-multiplier for offline
    if state.connection_status.value == "offline":
        f_status = 0.05
    elif state.connection_status.value == "intermittent":
        f_status = 0.60
    else:
        f_status = 1.0

    weights = [0.35, 0.25, 0.20, 0.20]
    factors = [f_hb, f_sig, f_stab, f_hist]
    raw = sum(w * f for w, f in zip(weights, factors))

    # Connection status as a hard multiplier
    raw *= f_status

    # OTA-specific: hard blockers applied as post-multiplier
    if command == "ota_install":
        if not state.is_parked:
            raw *= 0.0
        if state.battery_level < 50:
            raw *= 0.15
        if not state.ota_package_downloaded:
            raw *= 0.2
        if state.tcu_reconnect_count_1h > 3:
            raw *= 0.5

    final = raw * base_weight
    return max(0.0, min(1.0, final))


def _estimate_latency(state: VehicleState, command: str) -> int | None:
    base = COMMAND_BASE_LATENCY.get(command)
    if base is None:
        return None
    mult = 1.0
    if state.heartbeat_age_seconds > 60:
        mult += (state.heartbeat_age_seconds - 60) / 100
    if state.signal_strength_dbm < -85:
        mult += abs(state.signal_strength_dbm + 85) / 50
    if state.last_ack_latency_ms > 1000:
        mult += (state.last_ack_latency_ms - 1000) / 3000
    if state.connection_status.value == "intermittent":
        mult += 1.5
    return int(base * min(mult, 10.0))


def _get_risk_factors(state: VehicleState, command: str) -> list[str]:
    f = []
    if state.heartbeat_age_seconds > 120:
        f.append("heartbeat_stale")
    if state.heartbeat_age_seconds > 600:
        f.append("vehicle_likely_offline")
    if state.signal_strength_dbm < -100:
        f.append("signal_weak")
    elif state.signal_strength_dbm < -85:
        f.append("signal_degraded")
    if state.tcu_reconnect_count_1h > 5:
        f.append("tcu_flapping")
    if state.connection_status.value == "offline":
        f.append("vehicle_offline")
    elif state.connection_status.value == "intermittent":
        f.append("connection_unstable")
    if state.last_ack_latency_ms > 5000:
        f.append("high_latency")
    if state.commands_attempted_1h > 0 and state.commands_succeeded_1h / state.commands_attempted_1h < 0.5:
        f.append("repeated_failures")
    if command == "ota_install":
        if state.battery_level < 50:
            f.append("battery_low_ota")
        if not state.is_parked:
            f.append("ota_in_motion")
        if not state.ota_package_downloaded:
            f.append("ota_download_incomplete")
    if command == "remote_climate" and state.heartbeat_age_seconds > 60:
        f.append("climate_needs_sustained_connection")
    return f


def _risk_level(prob: float) -> RiskLevel:
    if prob >= 0.80:
        return RiskLevel.LOW
    if prob >= 0.55:
        return RiskLevel.MEDIUM
    if prob >= 0.30:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def predict_command(state: VehicleState, command: str) -> Prediction:
    command = command.lower().replace(" ", "_")
    prob = predict_command_probability(state, command)
    return Prediction(
        command=command,
        success_probability=round(prob, 3),
        risk_level=_risk_level(prob),
        risk_factors=_get_risk_factors(state, command),
        estimated_latency_ms=_estimate_latency(state, command),
        will_likely_fail=prob < 0.50,
    )
