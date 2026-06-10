"""Run this to verify the entire scoring + prediction + explanation + action pipeline."""

import sys
from datetime import datetime
from models import VehicleState, ConnectionStatus, ScoreBreakdown, RiskLevel
from scoring import compute_all_scores, reachability_score, ota_readiness_score, data_freshness_score
from predictor import predict_command, predict_command_probability
from explainer import explain_prediction, explain_vehicle_status
from actions import recommend_action


def v(name, **kwargs):
    defaults = dict(
        vin=f"WDB{name.upper()}001", name=name, model="Test",
        timestamp=datetime.now(),
        heartbeat_age_seconds=15, signal_strength_dbm=-55.0,
        network_type="4G", tcu_reconnect_count_1h=0,
        connection_status=ConnectionStatus.CONNECTED,
        last_ack_latency_ms=280, commands_attempted_1h=10,
        commands_succeeded_1h=9, battery_level=80.0,
        is_parked=True, is_charging=False,
        location_freshness_seconds=30,
    )
    defaults.update(kwargs)
    return VehicleState(**defaults)


def test_healthy():
    print("\n===== VEHICLE A: HEALTHY =====")
    state = v("alpha")
    scores = compute_all_scores(state)
    print(f"  Reach: {scores.reachability}  CMD: {scores.command_probability:.2f}  OTA: {scores.ota_readiness}  Fresh: {scores.data_freshness}  COMPOSITE: {scores.composite}")
    print(f"  Risk: {scores.risk_level.value}  Factors: {scores.factors}")

    pred = predict_command(state, "remote_lock")
    print(f"  Lock prediction: {pred.success_probability:.0%} [{pred.risk_level.value}]")

    expl = explain_vehicle_status(state, scores)
    print(f"  Message: \"{expl.customer_message}\"")

    assert scores.composite >= 85, f"Expected 85+, got {scores.composite}"
    assert scores.risk_level == RiskLevel.LOW
    print("  PASS")


def test_degrading():
    print("\n===== VEHICLE B: DEGRADING =====")

    # Stage 1: early
    s1 = v("beta", heartbeat_age_seconds=90, signal_strength_dbm=-88.0,
            tcu_reconnect_count_1h=5, connection_status=ConnectionStatus.INTERMITTENT,
            last_ack_latency_ms=3200, commands_attempted_1h=8, commands_succeeded_1h=5,
            location_freshness_seconds=120)
    sc1 = compute_all_scores(s1)
    print(f"  Stage1 — Composite: {sc1.composite}  Risk: {sc1.risk_level.value}")

    pred_climate = predict_command(s1, "remote_climate")
    expl = explain_prediction(pred_climate, s1)
    action = recommend_action(pred_climate, sc1)
    print(f"  Climate: {pred_climate.success_probability:.0%} [{pred_climate.risk_level.value}]")
    print(f"  Explain: \"{expl.customer_message}\"")
    print(f"  Action:  {action.action_type.value} — \"{action.label}\"")

    # Stage 2: critical
    s2 = v("beta", heartbeat_age_seconds=400, signal_strength_dbm=-112.0,
            tcu_reconnect_count_1h=12, connection_status=ConnectionStatus.OFFLINE,
            last_ack_latency_ms=15000, commands_attempted_1h=15, commands_succeeded_1h=3,
            location_freshness_seconds=500)
    sc2 = compute_all_scores(s2)
    print(f"  Stage2 — Composite: {sc2.composite}  Risk: {sc2.risk_level.value}")

    pred2 = predict_command(s2, "remote_lock")
    action2 = recommend_action(pred2, sc2)
    print(f"  Lock: {pred2.success_probability:.0%} Action: {action2.action_type.value}")

    assert sc2.composite < sc1.composite
    assert sc2.risk_level.value in ("high", "critical")
    print("  PASS")


def test_ota_blocked():
    print("\n===== VEHICLE C: OTA BLOCKED =====")
    state = v("gamma", battery_level=32.0, ota_package_available=True,
              ota_package_downloaded=True, signal_strength_dbm=-64.0)
    scores = compute_all_scores(state)
    print(f"  Composite: {scores.composite}  OTA: {scores.ota_readiness}  Factors: {scores.factors}")

    pred_ota = predict_command(state, "ota_install")
    expl = explain_prediction(pred_ota, state)
    action = recommend_action(pred_ota, scores)
    print(f"  OTA: {pred_ota.success_probability:.0%} [{pred_ota.risk_level.value}]")
    print(f"  Explain: \"{expl.customer_message}\"")
    print(f"  Action: {action.action_type.value} — \"{action.label}\"")

    pred_lock = predict_command(state, "remote_lock")
    print(f"  Lock (same vehicle): {pred_lock.success_probability:.0%} [{pred_lock.risk_level.value}]")

    assert pred_ota.will_likely_fail
    assert pred_lock.success_probability > 0.7
    assert "battery_low_ota" in scores.factors
    print("  PASS")


def test_degradation_detection():
    print("\n===== DEGRADATION DETECTION =====")
    history = [
        ScoreBreakdown(90, 0.9, 80, 90, 88, RiskLevel.LOW, False),
        ScoreBreakdown(80, 0.8, 80, 80, 78, RiskLevel.LOW, False),
        ScoreBreakdown(65, 0.65, 75, 70, 66, RiskLevel.MEDIUM, False),
        ScoreBreakdown(50, 0.5, 70, 55, 52, RiskLevel.HIGH, False),
    ]
    state = v("degrade", heartbeat_age_seconds=200, signal_strength_dbm=-95.0,
              tcu_reconnect_count_1h=7, connection_status=ConnectionStatus.INTERMITTENT,
              last_ack_latency_ms=4500, location_freshness_seconds=250)
    scores = compute_all_scores(state, history=history)
    print(f"  Is Degrading: {scores.is_degrading}  Composite: {scores.composite}")
    assert scores.is_degrading
    print("  PASS")


def test_all_commands():
    print("\n===== ALL COMMANDS (healthy vehicle) =====")
    state = v("cmdtest")
    scores = compute_all_scores(state)
    for cmd in ["remote_lock", "remote_unlock", "remote_climate", "remote_horn", "status_refresh", "ota_install"]:
        pred = predict_command(state, cmd)
        action = recommend_action(pred, scores)
        print(f"  {cmd:20s} -> {pred.success_probability:.0%} [{pred.risk_level.value:8s}] action={action.action_type.value}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  GUARDIAN ENGINE — FULL PIPELINE TEST")
    print("=" * 60)

    test_healthy()
    test_degrading()
    test_ota_blocked()
    test_degradation_detection()
    test_all_commands()

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED")
    print("=" * 60 + "\n")
