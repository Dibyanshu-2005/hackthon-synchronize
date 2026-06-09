"""
Guardian Engine API Client.
Connects to the real Guardian Engine (FastAPI on localhost:8000).
Falls back to mock data if engine is unavailable.
"""

import requests
import streamlit as st
from typing import Optional
from data.mock_data import (
    get_fleet_dataframe as mock_fleet_df,
    get_fleet_at_risk as mock_at_risk,
    get_command_history as mock_cmd_history,
    get_alerts as mock_alerts,
    predict_command as mock_predict,
    get_vehicle_detail as mock_vehicle_detail,
    get_vehicle_explanation as mock_vehicle_explain,
    VEHICLE_PROFILES,
)

ENGINE_BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 3


def _engine_available() -> bool:
    if "engine_status" not in st.session_state or st.session_state.get("_engine_check_stale", True):
        try:
            r = requests.get(f"{ENGINE_BASE_URL}/health", timeout=REQUEST_TIMEOUT)
            data = r.json()
            st.session_state["engine_status"] = data
            st.session_state["engine_online"] = True
            st.session_state["_engine_check_stale"] = False
            return True
        except Exception:
            st.session_state["engine_status"] = None
            st.session_state["engine_online"] = False
            st.session_state["_engine_check_stale"] = False
            return False
    return st.session_state.get("engine_online", False)


def get_engine_health() -> Optional[dict]:
    try:
        r = requests.get(f"{ENGINE_BASE_URL}/health", timeout=REQUEST_TIMEOUT)
        return r.json()
    except Exception:
        return None


def get_vehicles() -> dict:
    if _engine_available():
        try:
            r = requests.get(f"{ENGINE_BASE_URL}/vehicles", timeout=REQUEST_TIMEOUT)
            return r.json()
        except Exception:
            pass
    from data.mock_data import get_all_vehicles
    return get_all_vehicles()


def get_vehicle_detail(vin: str) -> dict:
    if _engine_available():
        try:
            r = requests.get(f"{ENGINE_BASE_URL}/vehicles/{vin}", timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return mock_vehicle_detail(vin)


def get_vehicle_explain(vin: str) -> dict:
    if _engine_available():
        try:
            r = requests.get(f"{ENGINE_BASE_URL}/vehicles/{vin}/explain", timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return mock_vehicle_explain(vin)


def predict_command(vin: str, command: str) -> dict:
    if _engine_available():
        try:
            r = requests.get(f"{ENGINE_BASE_URL}/vehicles/{vin}/predict/{command}", timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return mock_predict(vin, command)


def execute_command(vin: str, command: str) -> dict:
    if _engine_available():
        try:
            r = requests.post(f"{ENGINE_BASE_URL}/vehicles/{vin}/command/{command}", timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    pred = mock_predict(vin, command)
    pred["status"] = "executed" if pred["prediction"]["success_probability"] > 0.75 else "queued"
    pred["message"] = f"Command '{command}' processed."
    return pred


def get_vehicle_score(vin: str) -> Optional[dict]:
    if _engine_available():
        try:
            r = requests.get(f"{ENGINE_BASE_URL}/vehicles/{vin}/score", timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


def get_vehicle_history(vin: str) -> Optional[dict]:
    if _engine_available():
        try:
            r = requests.get(f"{ENGINE_BASE_URL}/vehicles/{vin}/history", timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


def get_fleet_metrics() -> dict:
    if _engine_available():
        try:
            r = requests.get(f"{ENGINE_BASE_URL}/fleet/metrics", timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return {
        "total_vehicles": len(VEHICLE_PROFILES),
        "average_score": 61.3,
        "at_risk_count": 4,
        "healthy_count": 3,
        "warning_count": 3,
        "critical_count": 2,
    }


def get_fleet_at_risk(threshold: float = 60.0) -> dict:
    if _engine_available():
        try:
            r = requests.get(f"{ENGINE_BASE_URL}/fleet/at-risk", params={"threshold": threshold}, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return mock_at_risk(threshold)


def load_vehicle_payload(payload: dict) -> Optional[dict]:
    if _engine_available():
        try:
            r = requests.post(f"{ENGINE_BASE_URL}/vehicles/load", json=payload, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


def is_live() -> bool:
    return st.session_state.get("engine_online", False)


def get_available_vins() -> list[str]:
    if _engine_available():
        try:
            r = requests.get(f"{ENGINE_BASE_URL}/vehicles", timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                return [v["vin"] for v in data.get("vehicles", [])]
        except Exception:
            pass
    return list(VEHICLE_PROFILES.keys())


COMMANDS = [
    "remote_lock",
    "remote_unlock",
    "remote_climate",
    "remote_horn",
    "status_refresh",
    "ota_install",
]
