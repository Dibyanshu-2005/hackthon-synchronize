"""
FastAPI application — Predictive Connected Experience Guardian.
Integrates P1's scoring/prediction engine with P2's explainer + actions.
Pipeline: Payload → payload_adapter → scoring → predictor → explainer → actions → API response
Simulator bridge: connects to Go simulator WebSocket, ingests 5 vehicles in real-time.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api_models import (
    APIScoreBreakdown,
    APIPrediction,
    SeverityLevel,
    VehiclePredictResponse,
    VehicleDetailResponse,
    VehicleExplainResponse,
    VehicleStatus,
    VehicleSummary,
    VehicleListResponse,
    AtRiskVehicle,
    AtRiskResponse,
    FleetMetricsResponse,
    CommandExecuteResponse,
    ScoreHistoryPoint,
    ScoreHistoryResponse,
)
from models import ScoreBreakdown, VehicleState
from payload_adapter import payload_to_vehicle_state
from scoring import compute_all_scores
from predictor import predict_command
from explainer import generate_explanation, get_status_explanation
from actions import recommend_action_api

logger = logging.getLogger("guardian")


# ──────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────

app = FastAPI(
    title="Predictive Connected Experience Guardian",
    version="1.0.0",
    description="Predicts command failures, explains issues, and recommends actions for connected vehicles.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# In-Memory Store
# ──────────────────────────────────────────────

vehicle_store: dict[str, dict] = {}          # VIN → raw payload
state_cache: dict[str, VehicleState] = {}    # VIN → VehicleState
score_history: dict[str, list[ScoreBreakdown]] = {}  # VIN → score history (for degradation detection)
api_score_history: dict[str, list[ScoreHistoryPoint]] = {}  # VIN → API history points


# ──────────────────────────────────────────────
# Helpers — Convert P1 models to API models
# ──────────────────────────────────────────────

def _to_api_scores(scores: ScoreBreakdown) -> APIScoreBreakdown:
    return APIScoreBreakdown(
        composite_score=scores.composite,
        reachability_score=scores.reachability,
        command_probability=scores.command_probability,
        ota_readiness_score=scores.ota_readiness,
        data_freshness_score=scores.data_freshness,
        risk_level=scores.risk_level.value,
        is_degrading=scores.is_degrading,
    )


def _to_api_prediction(pred) -> APIPrediction:
    return APIPrediction(
        command=pred.command,
        success_probability=pred.success_probability,
        risk_level=pred.risk_level.value,
        risk_factors=pred.risk_factors,
        estimated_latency_ms=pred.estimated_latency_ms,
        will_likely_fail=pred.will_likely_fail,
    )


def _severity_from_score(score: int) -> SeverityLevel:
    if score >= 75:
        return SeverityLevel.good
    if score >= 50:
        return SeverityLevel.warning
    return SeverityLevel.critical


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _process_vehicle(vin: str) -> tuple[VehicleState, ScoreBreakdown]:
    """Run the full scoring pipeline for a vehicle."""
    payload = vehicle_store[vin]
    state = payload_to_vehicle_state(payload)
    state_cache[vin] = state
    history = score_history.get(vin, [])
    scores = compute_all_scores(state, history)

    # Record history
    score_history.setdefault(vin, []).append(scores)
    score_history[vin] = score_history[vin][-50:]  # Keep last 50

    # Record API history point
    point = ScoreHistoryPoint(
        timestamp=_now_iso(),
        composite_score=scores.composite,
        reachability_score=scores.reachability,
        command_probability=scores.command_probability,
    )
    api_score_history.setdefault(vin, []).append(point)
    api_score_history[vin] = api_score_history[vin][-100:]

    return state, scores


# ──────────────────────────────────────────────
# Simulator Bridge — connects to Go simulator WS
# ──────────────────────────────────────────────

SIMULATOR_WS_URL = "ws://localhost:8080/ws"
_sim_task: asyncio.Task | None = None


async def _simulator_listener():
    """Background task: connect to simulator WebSocket, ingest payloads."""
    try:
        import websockets
    except ImportError:
        logger.warning("websockets not installed — simulator bridge disabled")
        return

    retry_delay = 2
    while True:
        try:
            async with websockets.connect(SIMULATOR_WS_URL) as ws:
                logger.info(f"✓ Connected to simulator at {SIMULATOR_WS_URL}")
                retry_delay = 2  # reset on successful connect
                async for message in ws:
                    try:
                        payload = json.loads(message)
                        vin = payload.get("vin")
                        if vin:
                            vehicle_store[vin] = payload
                            _process_vehicle(vin)
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f"Simulator message error: {e}")
        except Exception:
            logger.info(f"Simulator not available — retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30)  # exponential backoff, max 30s


# ──────────────────────────────────────────────
# Startup & Shutdown
# ──────────────────────────────────────────────

@app.on_event("startup")
async def load_seed_data():
    global _sim_task

    # Load seed payload file
    payload_path = Path(__file__).parent / "Payload_output.txt"
    if payload_path.exists():
        with open(payload_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        vin = payload.get("vin", "UNKNOWN")
        vehicle_store[vin] = payload
        state, scores = _process_vehicle(vin)
        print(f"✓ Loaded seed: {vin} | Composite: {scores.composite} | Risk: {scores.risk_level.value}")
    else:
        print(f"⚠ {payload_path} not found — no seed data loaded")

    # Start simulator bridge (non-blocking, auto-reconnects)
    _sim_task = asyncio.create_task(_simulator_listener())
    print(f"✓ Simulator bridge started (will connect to {SIMULATOR_WS_URL})")


@app.on_event("shutdown")
async def shutdown():
    if _sim_task:
        _sim_task.cancel()


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.get("/health")
async def health():
    sim_connected = _sim_task is not None and not _sim_task.done()
    return {
        "status": "ok",
        "service": "guardian-engine",
        "vehicles_loaded": len(vehicle_store),
        "simulator_bridge": "running" if sim_connected else "disconnected",
    }


# --- Vehicle List ---

@app.get("/vehicles", response_model=VehicleListResponse)
async def get_all_vehicles():
    summaries = []
    for vin in vehicle_store:
        state, scores = _process_vehicle(vin)
        summaries.append(VehicleSummary(
            vin=vin,
            model=state.model,
            composite_score=scores.composite,
            status=scores.risk_level.value,
            risk_factor_count=len(scores.factors),
            top_risk=scores.factors[0] if scores.factors else None,
        ))
    return VehicleListResponse(vehicles=summaries, total=len(summaries))


# --- Single Vehicle Detail ---

@app.get("/vehicles/{vin}", response_model=VehicleDetailResponse)
async def get_vehicle(vin: str):
    if vin not in vehicle_store:
        raise HTTPException(status_code=404, detail=f"Vehicle {vin} not found")

    payload = vehicle_store[vin]
    state, scores = _process_vehicle(vin)
    explanation = get_status_explanation(scores.factors, scores)

    return VehicleDetailResponse(
        vin=vin,
        model=state.model,
        region=payload.get("region", "Unknown"),
        scores=_to_api_scores(scores),
        status=VehicleStatus(
            overall=scores.risk_level.value,
            customer_message=explanation.customer_message,
            severity=explanation.severity,
        ),
        risk_factors=scores.factors,
        raw_payload=payload,
        updated_at=payload.get("updatedAt", _now_iso()),
    )


# --- Score Breakdown ---

@app.get("/vehicles/{vin}/score", response_model=APIScoreBreakdown)
async def get_vehicle_score(vin: str):
    if vin not in vehicle_store:
        raise HTTPException(status_code=404, detail=f"Vehicle {vin} not found")
    _, scores = _process_vehicle(vin)
    return _to_api_scores(scores)


# --- Predict Command (THE GOLDEN ENDPOINT) ---

@app.get("/vehicles/{vin}/predict/{command}", response_model=VehiclePredictResponse)
async def predict_command_endpoint(vin: str, command: str):
    if vin not in vehicle_store:
        raise HTTPException(status_code=404, detail=f"Vehicle {vin} not found")

    state, scores = _process_vehicle(vin)
    prediction = predict_command(state, command)
    explanation = generate_explanation(prediction.risk_factors, scores)
    action = recommend_action_api(prediction, scores, command)

    return VehiclePredictResponse(
        vin=vin,
        command=command,
        timestamp=_now_iso(),
        prediction=_to_api_prediction(prediction),
        scores=_to_api_scores(scores),
        explanation=explanation,
        recommended_action=action,
    )


# --- Execute Command (predict-first, then act) ---

@app.post("/vehicles/{vin}/command/{command}", response_model=CommandExecuteResponse)
async def execute_command(vin: str, command: str):
    if vin not in vehicle_store:
        raise HTTPException(status_code=404, detail=f"Vehicle {vin} not found")

    state, scores = _process_vehicle(vin)
    prediction = predict_command(state, command)
    explanation = generate_explanation(prediction.risk_factors, scores)
    action = recommend_action_api(prediction, scores, command)

    action_value = action.action.value
    if action_value == "do_nothing":
        status = "executed"
        message = f"Command '{command}' sent to vehicle successfully."
    elif action_value in ("retry_with_backoff", "queue_and_notify", "send_wake_ping"):
        status = "queued"
        message = f"Command '{command}' queued. {explanation.customer_message}"
    else:
        status = "blocked"
        message = f"Command '{command}' not sent. {explanation.customer_message}"

    return CommandExecuteResponse(
        vin=vin,
        command=command,
        prediction=_to_api_prediction(prediction),
        action_taken=action,
        explanation=explanation,
        status=status,
        message=message,
    )


# --- Explain Vehicle Status ---

@app.get("/vehicles/{vin}/explain", response_model=VehicleExplainResponse)
async def explain_vehicle(vin: str):
    if vin not in vehicle_store:
        raise HTTPException(status_code=404, detail=f"Vehicle {vin} not found")

    state, scores = _process_vehicle(vin)
    explanation = get_status_explanation(scores.factors, scores)

    return VehicleExplainResponse(
        vin=vin,
        customer_message=explanation.customer_message,
        severity=explanation.severity,
        technical_details=explanation.technical_details,
        risk_factors=scores.factors,
        timestamp=_now_iso(),
    )


# --- Score History ---

@app.get("/vehicles/{vin}/history", response_model=ScoreHistoryResponse)
async def get_history(vin: str):
    if vin not in vehicle_store:
        raise HTTPException(status_code=404, detail=f"Vehicle {vin} not found")
    return ScoreHistoryResponse(
        vin=vin,
        history=api_score_history.get(vin, []),
    )


# --- Fleet Metrics ---

@app.get("/fleet/metrics", response_model=FleetMetricsResponse)
async def fleet_metrics():
    if not vehicle_store:
        return FleetMetricsResponse(
            total_vehicles=0, average_score=0, at_risk_count=0,
            healthy_count=0, warning_count=0, critical_count=0,
        )

    all_scores = []
    healthy = warning = critical = 0
    for vin in vehicle_store:
        _, scores = _process_vehicle(vin)
        all_scores.append(scores.composite)
        sev = _severity_from_score(scores.composite)
        if sev == SeverityLevel.good:
            healthy += 1
        elif sev == SeverityLevel.warning:
            warning += 1
        else:
            critical += 1

    return FleetMetricsResponse(
        total_vehicles=len(vehicle_store),
        average_score=round(sum(all_scores) / len(all_scores), 1),
        at_risk_count=warning + critical,
        healthy_count=healthy,
        warning_count=warning,
        critical_count=critical,
    )


# --- At-Risk Vehicles ---

@app.get("/fleet/at-risk", response_model=AtRiskResponse)
async def at_risk_vehicles(threshold: float = 60):
    at_risk = []
    for vin in vehicle_store:
        _, scores = _process_vehicle(vin)
        if scores.composite < threshold:
            at_risk.append(AtRiskVehicle(
                vin=vin,
                composite_score=scores.composite,
                severity=_severity_from_score(scores.composite),
                top_risk=scores.factors[0] if scores.factors else None,
            ))
    return AtRiskResponse(threshold=threshold, at_risk_count=len(at_risk), vehicles=at_risk)


# --- Load Additional Vehicle Payloads ---

@app.post("/vehicles/load")
async def load_vehicle(payload: dict):
    vin = payload.get("vin")
    if not vin:
        raise HTTPException(status_code=400, detail="Payload must contain 'vin' field")
    vehicle_store[vin] = payload
    _, scores = _process_vehicle(vin)
    return {"status": "loaded", "vin": vin, "composite_score": scores.composite, "risk_level": scores.risk_level.value}
