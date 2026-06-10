"""
Actions module — decision engine that recommends what to do based on
prediction results and score breakdown.

Works with P1's models (Prediction, ScoreBreakdown from models.py).
Exports:
  - recommend_action(prediction, scores) → ActionResult (for P1's test)
  - recommend_action_api(prediction, scores, command) → RecommendedAction (for API)

Action types:
  do_nothing          — probability >= 85%, just send it
  retry_with_backoff  — 60-85%, send + auto-retry up to 3x
  queue_and_notify    — 40-60%, queue and notify on delivery
  suggest_alternative — 20-40%, suggest scheduling for later
  send_wake_ping      — vehicle may be sleeping, wake first
  escalate_to_support — <20% or score <20, needs human help
"""

from dataclasses import dataclass
from models import Prediction, ScoreBreakdown, ActionType as P1ActionType
from api_models import (
    RecommendedAction,
    ActionType as APIActionType,
    ActionDetails,
)


# ──────────────────────────────────────────────
# P1 Interface (what their test_engine.py expects)
# ──────────────────────────────────────────────

@dataclass
class ActionResult:
    """Return type for P1's test compatibility."""
    action_type: P1ActionType
    label: str
    reason: str
    estimated_wait_minutes: int | None = None
    fallback: P1ActionType | None = None


def recommend_action(prediction: Prediction, scores: ScoreBreakdown) -> ActionResult:
    """
    P1's interface: takes Prediction + ScoreBreakdown → ActionResult.
    Decision tree based on success_probability.
    """
    prob = prediction.success_probability
    command = prediction.command

    # --- Special case: OTA commands ---
    if command in ("ota_install", "ota_update", "software_update"):
        return _handle_ota(prediction, scores)

    # --- Main decision tree ---
    if prob >= 0.85:
        return ActionResult(
            action_type=P1ActionType.DO_NOTHING,
            label="Send Command",
            reason=f"High success probability ({prob:.0%})",
        )

    if prob >= 0.60:
        return ActionResult(
            action_type=P1ActionType.RETRY_WITH_BACKOFF,
            label="Send (will auto-retry)",
            reason=f"Moderate probability ({prob:.0%}) — will retry up to 3 times",
            estimated_wait_minutes=5,
            fallback=P1ActionType.QUEUE_AND_NOTIFY,
        )

    if prob >= 0.40:
        wait = _estimate_wait(prediction, scores)
        return ActionResult(
            action_type=P1ActionType.QUEUE_AND_NOTIFY,
            label="Queue & Notify Me",
            reason=f"Success probability {prob:.0%} — queuing for delivery when conditions improve",
            estimated_wait_minutes=wait,
            fallback=P1ActionType.SUGGEST_ALTERNATIVE,
        )

    if prob >= 0.20:
        # Vehicle might be sleeping
        sleeping_risks = {"heartbeat_stale", "vehicle_offline", "vehicle_likely_offline"}
        if sleeping_risks & set(prediction.risk_factors):
            return ActionResult(
                action_type=P1ActionType.SEND_WAKE_PING,
                label="Wake Vehicle",
                reason="Vehicle may be sleeping — sending wake ping",
                estimated_wait_minutes=10,
                fallback=P1ActionType.QUEUE_AND_NOTIFY,
            )

        return ActionResult(
            action_type=P1ActionType.SUGGEST_ALTERNATIVE,
            label="Schedule for Later",
            reason=f"Low probability ({prob:.0%}) — recommend scheduling",
            estimated_wait_minutes=30,
            fallback=P1ActionType.ESCALATE_TO_SUPPORT,
        )

    # prob < 0.20
    if scores.composite < 20:
        return ActionResult(
            action_type=P1ActionType.ESCALATE_TO_SUPPORT,
            label="Contact Support",
            reason=f"Vehicle health critically low (score: {scores.composite}) — may need service",
        )

    return ActionResult(
        action_type=P1ActionType.QUEUE_AND_NOTIFY,
        label="Queue & Notify Me",
        reason=f"Very low probability ({prob:.0%}) — queuing with extended wait",
        estimated_wait_minutes=60,
        fallback=P1ActionType.ESCALATE_TO_SUPPORT,
    )


def _handle_ota(prediction: Prediction, scores: ScoreBreakdown) -> ActionResult:
    """OTA-specific action logic."""
    blockers = []
    if "battery_low_ota" in prediction.risk_factors:
        blockers.append("Battery too low")
    if "ota_in_motion" in prediction.risk_factors:
        blockers.append("Vehicle in motion")
    if "ota_download_incomplete" in prediction.risk_factors:
        blockers.append("Download incomplete")

    if blockers:
        return ActionResult(
            action_type=P1ActionType.SUGGEST_ALTERNATIVE,
            label="Cannot Update Now",
            reason=" | ".join(blockers),
        )

    if prediction.success_probability >= 0.70:
        return ActionResult(
            action_type=P1ActionType.DO_NOTHING,
            label="Start Update",
            reason="Vehicle ready for update",
        )

    return ActionResult(
        action_type=P1ActionType.QUEUE_AND_NOTIFY,
        label="Schedule Update",
        reason=f"Conditions not ideal ({prediction.success_probability:.0%}) — will start when ready",
        estimated_wait_minutes=30,
    )


def _estimate_wait(prediction: Prediction, scores: ScoreBreakdown) -> int:
    """Estimate minutes until conditions might improve."""
    if scores.reachability >= 50:
        return 10
    if scores.reachability >= 30:
        return 20
    if scores.is_degrading:
        return 45
    return 30


# ──────────────────────────────────────────────
# API Interface (what our main.py uses)
# ──────────────────────────────────────────────

# Map P1 ActionType → API ActionType
_ACTION_MAP = {
    P1ActionType.DO_NOTHING: APIActionType.do_nothing,
    P1ActionType.RETRY_WITH_BACKOFF: APIActionType.retry_with_backoff,
    P1ActionType.QUEUE_AND_NOTIFY: APIActionType.queue_and_notify,
    P1ActionType.SEND_WAKE_PING: APIActionType.send_wake_ping,
    P1ActionType.SUGGEST_ALTERNATIVE: APIActionType.suggest_alternative,
    P1ActionType.ESCALATE_TO_SUPPORT: APIActionType.escalate_to_support,
}


def recommend_action_api(
    prediction: Prediction, scores: ScoreBreakdown, command: str = ""
) -> RecommendedAction:
    """
    API-friendly wrapper: returns Pydantic RecommendedAction for JSON responses.
    """
    # Temporarily set prediction.command if needed for OTA logic
    original_cmd = prediction.command
    if command:
        prediction.command = command

    result = recommend_action(prediction, scores)
    prediction.command = original_cmd

    api_action = _ACTION_MAP.get(result.action_type, APIActionType.queue_and_notify)
    fallback = _ACTION_MAP.get(result.fallback) if result.fallback else None

    details = ActionDetails(
        retry_count=3 if result.action_type == P1ActionType.RETRY_WITH_BACKOFF else 0,
        notify_on_delivery=result.action_type in (
            P1ActionType.QUEUE_AND_NOTIFY, P1ActionType.RETRY_WITH_BACKOFF, P1ActionType.SEND_WAKE_PING
        ),
        wake_ping_sent=result.action_type == P1ActionType.SEND_WAKE_PING,
    )

    return RecommendedAction(
        action=api_action,
        display_label=result.label,
        reason=result.reason,
        estimated_wait_minutes=result.estimated_wait_minutes,
        fallback_action=fallback,
        details=details,
    )
