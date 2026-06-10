================================================================================
  PREDICTIVE CONNECTED EXPERIENCE GUARDIAN — ENGINE + SIMULATOR
================================================================================

WHAT THIS IS
------------
A backend intelligence layer for connected vehicle apps. Instead of showing 
generic "Vehicle not reachable" errors, this system:

  1. PREDICTS if a command (lock, climate, OTA) will succeed BEFORE sending it
  2. EXPLAINS why in customer-friendly language
  3. RECOMMENDS the best action (send, retry, queue, escalate)

The Go simulator generates live telemetry for 5 vehicles. The Python engine 
scores, predicts, explains, and serves results via REST API.


ARCHITECTURE
------------
  Go Simulator (port 8080)  -->  WebSocket  -->  Python Engine (port 8000)  -->  Frontend
       5 vehicles                auto-push           scoring + prediction         REST API
       every 5 sec               real-time           + explanation + action


HOW TO RUN
----------
Step 1: Install Python dependencies
  cd Hackathon
  pip install -r requirements.txt

Step 2: Start the engine
  uvicorn main:app --reload --port 8000

Step 3 (optional): Start the simulator for live 5-vehicle data
  cd Simulator
  go run cmd/simulator/main.go -output websocket

  The engine auto-connects to the simulator. Without the simulator, 
  the engine runs with 1 seed vehicle (VIN_B_002) from Payload_output.txt.


API ENDPOINTS (all on http://localhost:8000)
--------------------------------------------
GET  /health                              — Service health + vehicle count
GET  /vehicles                            — List all vehicles with scores
GET  /vehicles/{vin}                      — Full vehicle detail + raw payload
GET  /vehicles/{vin}/score                — Score breakdown only
GET  /vehicles/{vin}/predict/{command}    — THE MAIN ONE: predict + explain + action
POST /vehicles/{vin}/command/{command}    — Execute command (predict-first)
GET  /vehicles/{vin}/explain              — Customer-facing status message
GET  /vehicles/{vin}/history              — Score history for charts
GET  /fleet/metrics                       — Fleet-level aggregation
GET  /fleet/at-risk                       — Vehicles below threshold
POST /vehicles/load                       — Load new vehicle payload JSON

Swagger interactive docs: http://localhost:8000/docs


EXAMPLE API CALL
----------------
GET /vehicles/VIN_B_002/predict/remote_lock

Returns:
{
  "vin": "VIN_B_002",
  "command": "remote_lock",
  "prediction": {
    "success_probability": 0.18,
    "risk_level": "critical",
    "risk_factors": ["heartbeat_stale", "signal_degraded", "tcu_flapping", ...],
    "will_likely_fail": true,
    "estimated_latency_ms": 8000
  },
  "scores": {
    "composite_score": 26,
    "reachability_score": 9,
    "command_probability": 0.175,
    "ota_readiness_score": 100,
    "data_freshness_score": 15
  },
  "explanation": {
    "customer_message": "Your vehicle appears to be unreachable. We'll try again when it reconnects.",
    "severity": "critical",
    "technical_details": "Active risks: Heartbeat Stale, ..."
  },
  "recommended_action": {
    "action": "queue_and_notify",
    "display_label": "Queue & Notify Me",
    "reason": "Very low probability (18%) - queuing with extended wait",
    "estimated_wait_minutes": 60,
    "fallback_action": "escalate_to_support"
  }
}


AVAILABLE COMMANDS FOR PREDICTION
----------------------------------
  remote_lock, remote_unlock, remote_climate, remote_horn, 
  status_refresh, ota_install


ACTION TYPES (what the frontend button should show)
----------------------------------------------------
  do_nothing          -> "Send Command"         (probability >= 85%)
  retry_with_backoff  -> "Send (will auto-retry)" (60-85%)
  queue_and_notify    -> "Queue & Notify Me"    (40-60%)
  suggest_alternative -> "Schedule for Later"   (20-40%)
  send_wake_ping      -> "Wake Vehicle"         (vehicle sleeping)
  escalate_to_support -> "Contact Support"      (<20% or score <20)


SEVERITY LEVELS (for UI colors)
--------------------------------
  good     -> green
  info     -> blue
  warning  -> yellow/orange
  critical -> red


VEHICLE VINs (from simulator fleet.json)
-----------------------------------------
  VIN_A_001  Model-S  IN-North  (starts: driving)
  VIN_B_002  Model-X  IN-South  (starts: parked)     <- also seed data
  VIN_C_003  Model-Y  IN-West   (starts: charging)
  VIN_D_004  Model-3  IN-East   (starts: idle)
  VIN_E_005  Model-X  IN-South  (starts: driving)


FILE STRUCTURE
--------------
  Hackathon/
  ├── main.py              <- FastAPI app, all routes, simulator bridge
  ├── api_models.py        <- Pydantic response schemas (API contracts)
  ├── explainer.py         <- Risk factors -> customer message (20+ templates)
  ├── actions.py           <- Decision engine (6 action types)
  ├── models.py            <- Core data models (P1: VehicleState, ScoreBreakdown)
  ├── scoring.py           <- Score computation (P1: reachability, freshness, etc.)
  ├── predictor.py         <- Command success prediction (P1: per-command probability)
  ├── payload_adapter.py   <- Converts raw JSON payload -> VehicleState
  ├── benchmarks.py        <- Industry-calibrated reference thresholds
  ├── test_engine.py       <- Integration tests (run: python test_engine.py)
  ├── requirements.txt     <- Python dependencies
  ├── Payload_output.txt   <- Seed vehicle payload (loaded at startup)
  └── Simulator/           <- Go simulator (generates live vehicle telemetry)
      ├── cmd/simulator/main.go
      ├── config/fleet.json
      ├── internal/engine/engine.go
      ├── internal/vehicle/vehicle.go
      ├── internal/generators/constraints.go
      ├── internal/generators/randomizer.go
      ├── internal/models/config.go
      ├── internal/models/telemetry.go
      ├── internal/output/output.go
      ├── internal/output/embed.go
      ├── internal/output/dashboard.html
      └── go.mod


WHO BUILT WHAT
--------------
  P1 (Scoring Engine): models.py, scoring.py, predictor.py, payload_adapter.py, benchmarks.py
  P2 (Explainer + API): explainer.py, actions.py, api_models.py, main.py
  P3 (Simulator):       Simulator/ folder (Go)
  P4 (Frontend):        YOUR JOB - consume the REST API above


FRONTEND INTEGRATION NOTES
---------------------------
- CORS is fully open (allow_origins=["*"]) — no proxy needed
- All responses are JSON
- The engine auto-updates vehicle data when simulator is running
- Without simulator, data is static (seed payload only)
- For real-time feel: poll GET /vehicles every 5-10 seconds
- Key endpoint for the app: GET /vehicles/{vin}/predict/{command}
- Use the "display_label" field from recommended_action as button text
- Use "severity" for color coding (good=green, warning=yellow, critical=red)
- Use "customer_message" as the main text shown to the user


TESTING
-------
  Run integration tests:     python test_engine.py
  Run server:                uvicorn main:app --reload --port 8000
  Test endpoint:             curl http://localhost:8000/vehicles/VIN_B_002/predict/remote_lock

================================================================================
