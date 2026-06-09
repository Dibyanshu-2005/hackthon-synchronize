"""
REAL-WORLD BENCHMARKS FOR CONNECTED VEHICLE SCORING
====================================================

Sources: Industry standards, OEM telemetry norms, cellular IoT specs.

TCU HEARTBEAT:
- Normal interval: 30-60 seconds
- Acceptable delay: up to 2 minutes (network jitter, sleep mode wakeup)
- Concerning: 2-5 minutes (possible signal loss, TCU entering sleep)
- Critical: 5-10 minutes (TCU offline or in deep sleep)
- Dead: 10+ minutes (hardware issue, no cellular, underground)

CELLULAR SIGNAL (RSSI in dBm):
- Excellent: > -65 dBm (full bars, 4G/5G reliable)
- Good: -65 to -75 dBm (reliable for commands)
- Fair: -75 to -90 dBm (commands work but with latency)
- Poor: -90 to -105 dBm (intermittent, commands may timeout)
- Very Poor: -105 to -115 dBm (barely connected, high failure rate)
- Dead: < -115 dBm (no usable connection)

TCU RECONNECTS:
- Normal: 0-1 per hour (routine handoffs between towers)
- Elevated: 2-4 per hour (mobile in edge-of-coverage areas)
- High: 5-10 per hour (unstable coverage, TCU antenna issue)
- Critical: 10+ per hour (hardware problem or severe coverage gap)
- For 15-min window: >3 in 15min = concerning, >6 = critical

COMMAND LATENCY (Cloud-to-Vehicle round trip):
- Excellent: < 2 seconds (vehicle awake, strong signal)
- Normal: 2-5 seconds (typical for parked vehicle wakeup)
- Elevated: 5-10 seconds (weak signal, TCU waking from sleep)
- High: 10-20 seconds (near-timeout territory)
- Timeout: 20-30 seconds (most OEMs timeout at 30s)
- Failed: > 30 seconds

COMMAND SUCCESS RATES (Industry benchmarks):
- Remote Lock/Unlock: 95-98% (lightweight, fast ACK)
- Remote Climate/Precondition: 88-93% (needs sustained conn, ECU wake)
- Remote Horn/Flash: 94-97% (simple command)
- Status Refresh: 90-95% (read-only but needs connection)
- OTA Install: 60-75% (complex, many preconditions)

BATTERY THRESHOLDS (for OTA):
- Most OEMs require: > 40-50% for installation
- Download can happen at any level
- EV: charging state preferred for long OTA installs
- ICE: engine off but accessory power available

CONNECTED EXPERIENCE SCORE BENCHMARKS:
- 90-100: Excellent — all features will work instantly
- 75-89:  Good — minor delays possible, reliable overall
- 55-74:  Fair — some commands may fail, user should expect delays
- 35-54:  Poor — most commands will fail or be very delayed
- 0-34:   Critical — vehicle effectively unreachable
"""

# Calibrated command base weights (max achievable probability under perfect conditions)
CALIBRATED_COMMAND_WEIGHTS = {
    "remote_lock": 0.98,       # Simple, fast, lightweight ACK
    "remote_unlock": 0.98,     # Same as lock
    "remote_climate": 0.92,    # Needs sustained connection + ECU wake + confirmation
    "remote_horn": 0.96,       # Simple but slightly more than lock (audio confirmation)
    "status_refresh": 0.95,    # Read operation, needs response payload
    "ota_install": 0.70,       # Complex multi-step, many preconditions
}

# Expected score ranges for known vehicle states
EXPECTED_BENCHMARKS = {
    "healthy_parked_home_wifi": {
        "reachability": (90, 100),
        "composite": (85, 100),
        "remote_lock_prob": (0.90, 1.0),
        "remote_climate_prob": (0.82, 0.95),
    },
    "healthy_driving_highway": {
        "reachability": (75, 95),
        "composite": (70, 90),
        "remote_lock_prob": (0.80, 0.95),
    },
    "underground_parking_no_signal": {
        "reachability": (0, 15),
        "composite": (0, 30),
        "remote_lock_prob": (0.0, 0.20),
    },
    "weak_signal_rural": {
        "reachability": (30, 60),
        "composite": (35, 65),
        "remote_lock_prob": (0.40, 0.70),
    },
    "tcu_degraded_high_reconnects": {
        "reachability": (15, 45),
        "composite": (25, 50),
        "remote_climate_prob": (0.15, 0.45),
    },
}
