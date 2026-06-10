from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class CommandType(str, Enum):
    REMOTE_LOCK = "remote_lock"
    REMOTE_UNLOCK = "remote_unlock"
    REMOTE_CLIMATE = "remote_climate"
    REMOTE_HORN = "remote_horn"
    STATUS_REFRESH = "status_refresh"
    OTA_INSTALL = "ota_install"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    INTERMITTENT = "intermittent"
    OFFLINE = "offline"


class ActionType(str, Enum):
    DO_NOTHING = "do_nothing"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    QUEUE_AND_NOTIFY = "queue_and_notify"
    SEND_WAKE_PING = "send_wake_ping"
    SUGGEST_ALTERNATIVE = "suggest_alternative"
    ESCALATE_TO_SUPPORT = "escalate_to_support"


class Severity(str, Enum):
    GOOD = "good"
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class VehicleState:
    vin: str
    name: str
    model: str
    timestamp: datetime

    heartbeat_age_seconds: int
    signal_strength_dbm: float
    network_type: str
    tcu_reconnect_count_1h: int
    connection_status: ConnectionStatus
    last_ack_latency_ms: int

    commands_attempted_1h: int
    commands_succeeded_1h: int
    last_command_type: Optional[str] = None
    last_command_status: Optional[str] = None

    ota_package_available: bool = False
    ota_package_downloaded: bool = False
    ota_blocker: Optional[str] = None

    battery_level: float = 80.0
    is_parked: bool = True
    is_charging: bool = False
    location_freshness_seconds: int = 30


@dataclass
class ScoreBreakdown:
    reachability: int
    command_probability: float
    ota_readiness: int
    data_freshness: int
    composite: int
    risk_level: RiskLevel
    is_degrading: bool
    factors: list = field(default_factory=list)


@dataclass
class Prediction:
    command: str
    success_probability: float
    risk_level: RiskLevel
    risk_factors: list
    estimated_latency_ms: Optional[int]
    will_likely_fail: bool


@dataclass
class Explanation:
    customer_message: str
    factors: list
    technical_details: str
    severity: Severity


@dataclass
class RecommendedAction:
    action_type: ActionType
    label: str
    description: str
    auto_retry: bool
    estimated_wait_min: Optional[int] = None
