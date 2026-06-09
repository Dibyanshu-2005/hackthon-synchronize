from models import VehicleState, ScoreBreakdown, RiskLevel


def _interpolate(value: float, breakpoints: list[tuple[float, float]]) -> float:
    if value <= breakpoints[0][0]:
        return breakpoints[0][1]
    if value >= breakpoints[-1][0]:
        return breakpoints[-1][1]
    for i in range(len(breakpoints) - 1):
        lo_t, lo_s = breakpoints[i]
        hi_t, hi_s = breakpoints[i + 1]
        if lo_t <= value <= hi_t:
            ratio = (value - lo_t) / (hi_t - lo_t)
            return lo_s + ratio * (hi_s - lo_s)
    return 0.0


def _wavg(weights: list[float], scores: list[float]) -> float:
    return sum(w * s for w, s in zip(weights, scores))


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def reachability_score(state: VehicleState) -> int:
    # Hard override: offline = max 10
    if state.connection_status.value == "offline":
        offline_score = _interpolate(state.heartbeat_age_seconds,
            [(0, 10), (300, 5), (600, 2), (900, 0)])
        return int(_clamp(offline_score, 0, 10))

    heartbeat = _interpolate(state.heartbeat_age_seconds,
        [(0, 100), (30, 100), (60, 85), (120, 65), (300, 35), (600, 10), (900, 0)])

    # Zero reconnects with dead signal = not a positive (can't reconnect if no signal)
    if state.signal_strength_dbm < -110:
        reconnect = 0.0
    else:
        reconnect = _interpolate(state.tcu_reconnect_count_1h,
            [(0, 100), (2, 85), (5, 60), (8, 35), (12, 15), (15, 0)])

    signal = _interpolate(state.signal_strength_dbm,
        [(-120, 0), (-110, 10), (-100, 35), (-85, 60), (-70, 85), (-55, 100)])
    latency = _interpolate(state.last_ack_latency_ms,
        [(0, 100), (300, 100), (800, 80), (2000, 55), (5000, 30), (10000, 10), (15000, 0)])

    raw = _wavg([0.35, 0.25, 0.20, 0.20], [heartbeat, reconnect, signal, latency])

    # Intermittent cap: never score above 65 if connection is unstable
    if state.connection_status.value == "intermittent":
        raw = min(raw, 65)

    return int(_clamp(raw))


def ota_readiness_score(state: VehicleState) -> int:
    if not state.ota_package_available:
        return 100

    # Hard blockers: if any critical condition fails, cap score low
    if not state.is_parked:
        return 5  # Cannot install while driving — hard block
    if state.battery_level < 20:
        return 5  # Critically low battery — hard block

    if state.battery_level < 50:
        batt = ((state.battery_level - 20) / 30) * 50
    else:
        batt = 50 + ((state.battery_level - 50) / 50) * 50

    conn = 100.0 if state.tcu_reconnect_count_1h <= 2 else max(0, 100 - state.tcu_reconnect_count_1h * 12)
    parked = 100.0  # Already verified above
    download = 100.0 if state.ota_package_downloaded else 20.0

    return int(_clamp(_wavg([0.40, 0.25, 0.20, 0.15], [batt, conn, parked, download])))


def data_freshness_score(state: VehicleState) -> int:
    hb_fresh = _interpolate(state.heartbeat_age_seconds,
        [(0, 100), (30, 100), (60, 80), (180, 50), (600, 20), (1200, 0)])
    loc_fresh = _interpolate(state.location_freshness_seconds,
        [(0, 100), (60, 95), (300, 70), (900, 40), (1800, 15), (3600, 0)])
    status_map = {"connected": 100.0, "intermittent": 50.0, "offline": 10.0}
    conn_fresh = status_map.get(state.connection_status.value, 0.0)

    return int(_clamp(_wavg([0.50, 0.25, 0.25], [hb_fresh, loc_fresh, conn_fresh])))


def composite_cx_score(reachability: int, command_prob: float, ota_readiness: int, freshness: int) -> int:
    cmd = command_prob * 100
    return int(_clamp(_wavg([0.40, 0.30, 0.15, 0.15], [reachability, cmd, ota_readiness, freshness])))


def _risk_level(composite: int) -> RiskLevel:
    if composite >= 75:
        return RiskLevel.LOW
    if composite >= 55:
        return RiskLevel.MEDIUM
    if composite >= 35:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def _risk_factors(state: VehicleState) -> list[str]:
    f = []
    if state.heartbeat_age_seconds > 120:
        f.append("heartbeat_stale")
    if state.signal_strength_dbm < -100:
        f.append("signal_weak")
    if state.tcu_reconnect_count_1h > 5:
        f.append("tcu_flapping")
    if state.last_ack_latency_ms > 5000:
        f.append("high_latency")
    if state.connection_status.value == "offline":
        f.append("vehicle_offline")
    elif state.connection_status.value == "intermittent":
        f.append("connection_unstable")
    if state.battery_level < 50 and state.ota_package_available:
        f.append("battery_low_ota")
    if state.battery_level < 20:
        f.append("battery_critical")
    if not state.is_parked and state.ota_package_available:
        f.append("ota_in_motion")
    if state.commands_attempted_1h > 0 and state.commands_succeeded_1h / state.commands_attempted_1h < 0.5:
        f.append("repeated_failures")
    if state.heartbeat_age_seconds > 300 and state.location_freshness_seconds > 600:
        f.append("data_stale")
    return f


def compute_all_scores(state: VehicleState, history: list[ScoreBreakdown] | None = None) -> ScoreBreakdown:
    from predictor import predict_command_probability

    reach = reachability_score(state)
    ota = ota_readiness_score(state)
    freshness = data_freshness_score(state)

    cmd_probs = [
        predict_command_probability(state, "remote_lock"),
        predict_command_probability(state, "remote_climate"),
        predict_command_probability(state, "status_refresh"),
    ]
    avg_cmd = sum(cmd_probs) / len(cmd_probs)

    composite = composite_cx_score(reach, avg_cmd, ota, freshness)
    risk = _risk_level(composite)
    factors = _risk_factors(state)

    is_degrading = False
    if history and len(history) >= 3:
        recent = [h.composite for h in history[-5:]]
        if len(recent) >= 3:
            diffs = [recent[i+1] - recent[i] for i in range(len(recent)-1)]
            declining = sum(1 for d in diffs if d < 0)
            is_degrading = declining >= len(diffs) * 0.6 and recent[-1] < recent[0] - 10

    return ScoreBreakdown(
        reachability=reach,
        command_probability=round(avg_cmd, 3),
        ota_readiness=ota,
        data_freshness=freshness,
        composite=composite,
        risk_level=risk,
        is_degrading=is_degrading,
        factors=factors,
    )
