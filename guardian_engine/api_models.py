"""
Pydantic response schemas for the Predictive Connected Experience Guardian.
API response models — maps P1's dataclass outputs to JSON responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


# --- Enums ---

class SeverityLevel(str, Enum):
    good = "good"
    info = "info"
    warning = "warning"
    critical = "critical"


class ActionType(str, Enum):
    do_nothing = "do_nothing"
    retry_with_backoff = "retry_with_backoff"
    queue_and_notify = "queue_and_notify"
    suggest_alternative = "suggest_alternative"
    escalate_to_support = "escalate_to_support"
    send_wake_ping = "send_wake_ping"


# --- Score Models (matches P1's ScoreBreakdown) ---

class APIScoreBreakdown(BaseModel):
    composite_score: int = Field(..., ge=0, le=100)
    reachability_score: int = Field(..., ge=0, le=100)
    command_probability: float = Field(..., ge=0, le=1)
    ota_readiness_score: int = Field(..., ge=0, le=100)
    data_freshness_score: int = Field(..., ge=0, le=100)
    risk_level: str
    is_degrading: bool = False


class APIPrediction(BaseModel):
    command: str
    success_probability: float = Field(..., ge=0, le=1)
    risk_level: str
    risk_factors: list[str] = []
    estimated_latency_ms: Optional[int] = None
    will_likely_fail: bool = False


# --- P2 Models ---

class Explanation(BaseModel):
    customer_message: str
    severity: SeverityLevel
    technical_details: str = ""


class ActionDetails(BaseModel):
    retry_count: int = 0
    notify_on_delivery: bool = False
    wake_ping_sent: bool = False
    support_ticket_id: Optional[str] = None
    scheduled_time: Optional[str] = None


class RecommendedAction(BaseModel):
    action: ActionType
    display_label: str
    reason: str
    estimated_wait_minutes: Optional[int] = None
    fallback_action: Optional[ActionType] = None
    details: ActionDetails = ActionDetails()


# --- API Response Envelopes ---

class VehiclePredictResponse(BaseModel):
    vin: str
    command: str
    timestamp: str
    prediction: APIPrediction
    scores: APIScoreBreakdown
    explanation: Explanation
    recommended_action: RecommendedAction


class VehicleStatus(BaseModel):
    overall: str
    customer_message: str
    severity: SeverityLevel


class VehicleDetailResponse(BaseModel):
    vin: str
    model: str
    region: str
    scores: APIScoreBreakdown
    status: VehicleStatus
    risk_factors: list[str]
    raw_payload: dict[str, Any]
    updated_at: str


class VehicleExplainResponse(BaseModel):
    vin: str
    customer_message: str
    severity: SeverityLevel
    technical_details: str
    risk_factors: list[str]
    timestamp: str


class VehicleSummary(BaseModel):
    vin: str
    model: str
    composite_score: int
    status: str
    risk_factor_count: int
    top_risk: Optional[str] = None


class VehicleListResponse(BaseModel):
    vehicles: list[VehicleSummary]
    total: int


class AtRiskVehicle(BaseModel):
    vin: str
    composite_score: int
    severity: SeverityLevel
    top_risk: Optional[str] = None


class AtRiskResponse(BaseModel):
    threshold: float
    at_risk_count: int
    vehicles: list[AtRiskVehicle]


class FleetMetricsResponse(BaseModel):
    total_vehicles: int
    average_score: float
    at_risk_count: int
    healthy_count: int
    warning_count: int
    critical_count: int


class CommandExecuteResponse(BaseModel):
    vin: str
    command: str
    prediction: APIPrediction
    action_taken: RecommendedAction
    explanation: Explanation
    status: str
    message: str


class ScoreHistoryPoint(BaseModel):
    timestamp: str
    composite_score: int
    reachability_score: int
    command_probability: float


class ScoreHistoryResponse(BaseModel):
    vin: str
    history: list[ScoreHistoryPoint]
