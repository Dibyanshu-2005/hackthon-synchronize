package generators

import (
	"fmt"
	"math"
	"math/rand"
	"time"
	"vehicle-telemetry-simulator/internal/models"
)

var knownDTCCodes = []string{
	"P0300", "P0420", "P0171", "P0442", "P0455",
	"C1201", "C0035", "B1000", "U0100", "U0073",
	"P0128", "P0401", "P0507", "P0700", "P1000",
}

var commandTypes = []string{
	"remote_lock", "remote_unlock", "remote_climate_start",
	"remote_climate_stop", "remote_horn", "remote_flash",
	"remote_engine_start", "remote_engine_stop",
}

var appEventTypes = []string{
	"remote_lock_clicked", "remote_unlock_clicked", "remote_climate_clicked",
	"vehicle_status_refresh", "trip_history_viewed", "charging_schedule_set",
}

var securityEventTypes = []string{
	"intrusion_detected", "certificate_expiry_warning", "unauthorized_access_attempt",
	"firmware_tamper_detected", "anomalous_can_bus_traffic",
}

// ApplyDrivingConstraints updates driving state with realistic physics-based constraints.
func ApplyDrivingConstraints(t *models.Telemetry, drivingMode string) {
	ds := &t.DrivingState

	switch drivingMode {
	case "parked":
		ds.SpeedKmph = 0
		ds.AccelerationMps2 = 0
		ds.Gear = "park"
		ds.BrakeStatus = "engaged"
		ds.SteeringAngleDegrees = 0
		ds.DrivingMode = "parked"
		t.VehicleHealth.EngineStatus = "off"

	case "idle":
		ds.SpeedKmph = 0
		ds.AccelerationMps2 = 0
		ds.Gear = RandomChoice([]string{"park", "neutral"})
		ds.BrakeStatus = "engaged"
		ds.SteeringAngleDegrees = 0
		ds.DrivingMode = "idle"
		t.VehicleHealth.EngineStatus = "on"

	case "driving":
		targetSpeed := Drift(ds.SpeedKmph, 15, 140, 15)
		accel := (targetSpeed - ds.SpeedKmph) / 3.6 // rough m/s² approx
		accel = Clamp(accel, -5.0, 4.0)

		ds.SpeedKmph = RoundTo(targetSpeed, 1)
		ds.AccelerationMps2 = RoundTo(accel, 2)
		ds.Gear = "drive"
		if ds.SpeedKmph > 100 {
			ds.Gear = RandomChoice([]string{"drive", "sport"})
		}
		ds.BrakeStatus = "released"
		if accel < -1.0 {
			ds.BrakeStatus = "engaged"
		}
		ds.SteeringAngleDegrees = RoundTo(GaussianDrift(ds.SteeringAngleDegrees, -45, 45, 8), 1)
		ds.DrivingMode = "driving"
		t.VehicleHealth.EngineStatus = "on"

	case "charging":
		ds.SpeedKmph = 0
		ds.AccelerationMps2 = 0
		ds.Gear = "park"
		ds.BrakeStatus = "engaged"
		ds.SteeringAngleDegrees = 0
		ds.DrivingMode = "parked"
		t.VehicleHealth.EngineStatus = "off"
	}
}

// ApplyBatteryConstraints updates battery/charging state based on driving mode.
func ApplyBatteryConstraints(t *models.Telemetry, drivingMode string) {
	bc := &t.BatteryCharging

	switch drivingMode {
	case "driving":
		// Drain: faster at higher speeds. ~0.3-1.5% per tick
		drainRate := 0.3 + (t.DrivingState.SpeedKmph/140.0)*1.2
		drainRate += (rand.Float64() - 0.5) * 0.2
		bc.BatteryLevel = RoundTo(Clamp(bc.BatteryLevel-drainRate, 0, 100), 1)
		bc.ChargingStatus = "not_charging"
		bc.ChargingType = "none"
		bc.ChargingPowerKw = 0
		// Battery temp rises with speed
		bc.BatteryTemperatureCelsius = RoundTo(Drift(bc.BatteryTemperatureCelsius, 25, 55, 1.5), 1)

	case "charging":
		chargeType := bc.ChargingType
		if chargeType == "none" {
			chargeType = WeightedChoice([]string{"ac_slow", "ac_fast", "dc_fast"}, []float64{0.4, 0.35, 0.25})
		}
		bc.ChargingType = chargeType

		var chargeRate float64
		switch chargeType {
		case "ac_slow":
			bc.ChargingPowerKw = RoundTo(Drift(7.2, 6.0, 7.4, 0.3), 1)
			chargeRate = 0.4 + rand.Float64()*0.2
		case "ac_fast":
			bc.ChargingPowerKw = RoundTo(Drift(11.0, 9.0, 11.5, 0.5), 1)
			chargeRate = 0.7 + rand.Float64()*0.3
		case "dc_fast":
			bc.ChargingPowerKw = RoundTo(Drift(50.0, 40.0, 150.0, 10), 1)
			chargeRate = 1.5 + rand.Float64()*1.0
		}
		// Taper charging above 80%
		if bc.BatteryLevel > 80 {
			chargeRate *= 0.4
			bc.ChargingPowerKw *= 0.5
		}
		bc.BatteryLevel = RoundTo(Clamp(bc.BatteryLevel+chargeRate, 0, 100), 1)
		bc.ChargingStatus = "charging"
		// Battery temp rises while charging
		bc.BatteryTemperatureCelsius = RoundTo(Drift(bc.BatteryTemperatureCelsius, 28, 48, 1.0), 1)

	default: // parked, idle
		bc.ChargingStatus = "not_charging"
		bc.ChargingType = "none"
		bc.ChargingPowerKw = 0
		// Slow passive drain
		if Chance(0.3) {
			bc.BatteryLevel = RoundTo(Clamp(bc.BatteryLevel-0.05, 0, 100), 1)
		}
		// Battery cools toward ambient
		ambient := 30.0 + rand.Float64()*5
		bc.BatteryTemperatureCelsius = RoundTo(bc.BatteryTemperatureCelsius+(ambient-bc.BatteryTemperatureCelsius)*0.1, 1)
	}

	// Range correlates with battery: ~4.2 km per percent (typical EV)
	efficiency := 3.8 + rand.Float64()*0.8 // 3.8-4.6 km/%
	bc.RangeKm = RoundTo(bc.BatteryLevel*efficiency, 0)
}

// ApplyVehicleHealthConstraints updates health metrics based on state.
func ApplyVehicleHealthConstraints(t *models.Telemetry, drivingMode string) {
	vh := &t.VehicleHealth

	switch drivingMode {
	case "driving":
		// Temperature rises while driving
		vh.TemperatureCelsius = RoundTo(Drift(vh.TemperatureCelsius, 70, 105, 3), 1)
		// Fuel consumption
		vh.FuelLevelPercent = RoundTo(Clamp(vh.FuelLevelPercent-0.1-rand.Float64()*0.3, 0, 100), 1)
		// Slow oil/coolant degradation
		if Chance(0.05) {
			vh.OilLevelPercent = RoundTo(Clamp(vh.OilLevelPercent-0.1, 0, 100), 1)
		}
		if Chance(0.03) {
			vh.CoolantLevelPercent = RoundTo(Clamp(vh.CoolantLevelPercent-0.1, 0, 100), 1)
		}
	default:
		// Cool down when not driving
		ambient := 28.0 + rand.Float64()*10
		vh.TemperatureCelsius = RoundTo(vh.TemperatureCelsius+(ambient-vh.TemperatureCelsius)*0.15, 1)
	}

	// Compute health score from component levels
	score := int((vh.FuelLevelPercent + vh.CoolantLevelPercent + vh.OilLevelPercent) / 3.0)
	// Penalize high temp
	if vh.TemperatureCelsius > 95 {
		score -= int((vh.TemperatureCelsius - 95) * 2)
	}
	// Penalize active DTCs
	score -= t.Diagnostics.ActiveDTCCount * 5
	vh.VehicleHealthScore = ClampInt(score, 0, 100)

	// Overall status from score
	switch {
	case vh.VehicleHealthScore >= 85:
		vh.OverallStatus = "healthy"
	case vh.VehicleHealthScore >= 60:
		vh.OverallStatus = "warning"
	default:
		vh.OverallStatus = "critical"
	}
}

// ApplyECUConstraints updates ECU health based on vehicle state.
func ApplyECUConstraints(t *models.Telemetry, drivingMode string) {
	ecu := &t.ECUHealth

	switch drivingMode {
	case "driving":
		ecu.TCUCpuUsagePercent = RoundTo(Drift(ecu.TCUCpuUsagePercent, 30, 85, 8), 1)
		ecu.TCUMemoryUsagePercent = RoundTo(Drift(ecu.TCUMemoryUsagePercent, 40, 80, 5), 1)
		ecu.LastEcuHeartbeatAgeSeconds = DriftInt(ecu.LastEcuHeartbeatAgeSeconds, 1, 30, 5)
	case "idle":
		ecu.TCUCpuUsagePercent = RoundTo(Drift(ecu.TCUCpuUsagePercent, 10, 45, 5), 1)
		ecu.TCUMemoryUsagePercent = RoundTo(Drift(ecu.TCUMemoryUsagePercent, 20, 50, 3), 1)
		ecu.LastEcuHeartbeatAgeSeconds = DriftInt(ecu.LastEcuHeartbeatAgeSeconds, 1, 60, 10)
	default: // parked, charging
		ecu.TCUCpuUsagePercent = RoundTo(Drift(ecu.TCUCpuUsagePercent, 5, 30, 4), 1)
		ecu.TCUMemoryUsagePercent = RoundTo(Drift(ecu.TCUMemoryUsagePercent, 15, 40, 3), 1)
		// Heartbeat can age if connectivity is poor
		if t.Connectivity.ConnectionState == "unstable" || t.Connectivity.ConnectionState == "disconnected" {
			ecu.LastEcuHeartbeatAgeSeconds = DriftInt(ecu.LastEcuHeartbeatAgeSeconds, 60, 3600, 120)
		} else {
			ecu.LastEcuHeartbeatAgeSeconds = DriftInt(ecu.LastEcuHeartbeatAgeSeconds, 1, 30, 5)
		}
	}

	// ECU status from CPU usage
	switch {
	case ecu.TCUCpuUsagePercent > 80:
		ecu.PrimaryEcuStatus = "degraded"
	case ecu.TCUCpuUsagePercent > 95:
		ecu.PrimaryEcuStatus = "critical"
	default:
		ecu.PrimaryEcuStatus = "healthy"
	}
}

// ApplyConnectivityConstraints updates connectivity with realistic network behavior.
func ApplyConnectivityConstraints(t *models.Telemetry, drivingMode string) {
	conn := &t.Connectivity
	now := time.Now()

	// Network type can shift occasionally
	if Chance(0.05) {
		conn.NetworkType = WeightedChoice(
			[]string{"5G", "4G", "3G", "2G"},
			[]float64{0.15, 0.55, 0.2, 0.1},
		)
	}

	// Signal strength depends on network type and region
	switch conn.NetworkType {
	case "5G":
		conn.SignalStrengthPercent = RoundTo(Drift(conn.SignalStrengthPercent, 50, 100, 8), 0)
	case "4G":
		conn.SignalStrengthPercent = RoundTo(Drift(conn.SignalStrengthPercent, 25, 95, 10), 0)
	case "3G":
		conn.SignalStrengthPercent = RoundTo(Drift(conn.SignalStrengthPercent, 10, 70, 12), 0)
	case "2G":
		conn.SignalStrengthPercent = RoundTo(Drift(conn.SignalStrengthPercent, 5, 40, 8), 0)
	}

	// Latency inversely correlated with signal strength
	baseLatency := 50.0 + (100-conn.SignalStrengthPercent)*15
	conn.LatencyMs = RoundTo(GaussianDrift(conn.LatencyMs, 20, 2000, baseLatency*0.15), 0)

	// Connection state from signal
	switch {
	case conn.SignalStrengthPercent >= 60:
		conn.ConnectionState = "connected"
		conn.LastConnectedTime = now
		conn.ReconnectCountLast15Min = DriftInt(conn.ReconnectCountLast15Min, 0, 2, 1)
	case conn.SignalStrengthPercent >= 30:
		conn.ConnectionState = WeightedChoice([]string{"connected", "unstable"}, []float64{0.6, 0.4})
		if conn.ConnectionState == "connected" {
			conn.LastConnectedTime = now
		}
		conn.ReconnectCountLast15Min = DriftInt(conn.ReconnectCountLast15Min, 2, 10, 3)
	default:
		conn.ConnectionState = WeightedChoice([]string{"unstable", "disconnected"}, []float64{0.5, 0.5})
		conn.ReconnectCountLast15Min = DriftInt(conn.ReconnectCountLast15Min, 5, 20, 5)
	}

	// Heartbeat age: grows when disconnected
	if conn.ConnectionState == "connected" {
		conn.LastHeartbeatMinutes = RoundTo(Drift(conn.LastHeartbeatMinutes, 0, 5, 2), 0)
	} else {
		conn.LastHeartbeatMinutes = RoundTo(Clamp(conn.LastHeartbeatMinutes+float64(1+rand.Intn(5)), 0, 120), 0)
	}

	conn.DeviceTwinAgeMinutes = RoundTo(conn.LastHeartbeatMinutes+Drift(0, 0, 10, 3), 0)
}

// ApplyDiagnosticsConstraints generates/clears DTCs based on health.
func ApplyDiagnosticsConstraints(t *models.Telemetry) {
	diag := &t.Diagnostics

	// Chance of new DTC appearing
	if t.VehicleHealth.VehicleHealthScore < 70 && Chance(0.1) {
		newCode := RandomChoice(knownDTCCodes)
		found := false
		for _, c := range diag.DTCCodes {
			if c == newCode {
				found = true
				break
			}
		}
		if !found && len(diag.DTCCodes) < 5 {
			diag.DTCCodes = append(diag.DTCCodes, newCode)
		}
	}

	// Chance of clearing a DTC (repair/self-heal)
	if len(diag.DTCCodes) > 0 && t.VehicleHealth.VehicleHealthScore > 80 && Chance(0.15) {
		idx := rand.Intn(len(diag.DTCCodes))
		diag.DTCCodes = append(diag.DTCCodes[:idx], diag.DTCCodes[idx+1:]...)
	}

	diag.ActiveDTCCount = len(diag.DTCCodes)
	switch {
	case diag.ActiveDTCCount == 0:
		diag.HighestDTCSeverity = "none"
	case diag.ActiveDTCCount <= 2:
		diag.HighestDTCSeverity = WeightedChoice([]string{"low", "medium"}, []float64{0.6, 0.4})
	default:
		diag.HighestDTCSeverity = WeightedChoice([]string{"medium", "high", "critical"}, []float64{0.4, 0.4, 0.2})
	}
}

// ApplyOTAConstraints progresses OTA updates only when parked.
func ApplyOTAConstraints(t *models.Telemetry, drivingMode string) {
	ota := &t.OTA

	switch ota.OTAStatus {
	case "not_started":
		// Randomly make an OTA package available
		if Chance(0.02) {
			ota.OTAPackageAvailable = true
		}
		if ota.OTAPackageAvailable && drivingMode == "parked" && Chance(0.3) {
			ota.OTAStatus = "downloading"
			ota.OTAProgressPercent = 0
		}

	case "downloading":
		if drivingMode != "parked" {
			ota.OTAStatus = "paused"
			break
		}
		progress := 5.0 + rand.Float64()*10
		// Slower with bad connectivity
		if t.Connectivity.ConnectionState != "connected" {
			progress *= 0.2
		}
		ota.OTAProgressPercent = RoundTo(Clamp(ota.OTAProgressPercent+progress, 0, 100), 1)
		if ota.OTAProgressPercent >= 100 {
			ota.OTAStatus = "installing"
			ota.OTAProgressPercent = 100
		}
		// Random download error
		if Chance(0.02) {
			ota.OTAStatus = "failed"
			ota.OTAErrorCodes = append(ota.OTAErrorCodes, "OTA_DOWNLOAD_INTERRUPTED")
		}

	case "installing":
		if drivingMode != "parked" {
			ota.OTAStatus = "failed"
			ota.OTAErrorCodes = append(ota.OTAErrorCodes, "OTA_INSTALL_INTERRUPTED_BY_DRIVE")
			break
		}
		if Chance(0.4) {
			ota.OTAStatus = "completed"
			t.SoftwareInventory.ComponentsOutdatedCount = ClampInt(t.SoftwareInventory.ComponentsOutdatedCount-1, 0, 10)
			if len(t.SoftwareInventory.CriticalComponentsOutdated) > 0 {
				t.SoftwareInventory.CriticalComponentsOutdated = t.SoftwareInventory.CriticalComponentsOutdated[1:]
			}
			t.SoftwareInventory.LastSoftwareInventoryUpdate = time.Now()
		}
		if Chance(0.05) {
			ota.OTAStatus = "failed"
			ota.OTAErrorCodes = append(ota.OTAErrorCodes, "OTA_INSTALL_CHECKSUM_FAIL")
		}

	case "paused":
		if drivingMode == "parked" {
			ota.OTAStatus = "downloading"
		}

	case "completed", "failed":
		// Reset after some time
		if Chance(0.01) {
			ota.OTAStatus = "not_started"
			ota.OTAProgressPercent = 0
			ota.OTAPackageAvailable = false
			ota.OTAErrorCodes = []string{}
			ota.UpdateID = fmt.Sprintf("OTA_%d_%02d_%03d", time.Now().Year(), time.Now().Month(), rand.Intn(999)+1)
			ota.TargetVersion = fmt.Sprintf("TCU-%d.%d.%d", 3+rand.Intn(2), rand.Intn(10), rand.Intn(10))
		}
	}
}

// ApplyCommandLifecycleConstraints simulates remote command events.
func ApplyCommandLifecycleConstraints(t *models.Telemetry) {
	cmd := &t.CommandLifecycle
	now := time.Now()

	// Randomly trigger new commands
	if Chance(0.08) {
		cmd.LastCommandID = fmt.Sprintf("CMD_%05d", rand.Intn(99999))
		cmd.LastCommandType = RandomChoice(commandTypes)
		cmd.LastCommandIssueTime = now

		if t.Connectivity.ConnectionState == "connected" {
			latency := 200 + rand.Intn(2000)
			cmd.LastCommandLatencyMs = latency
			execTime := now.Add(time.Duration(latency) * time.Millisecond)
			cmd.LastCommandExecuteTime = &execTime
			cmd.LastCommandResponseTime = execTime.Add(time.Duration(50+rand.Intn(200)) * time.Millisecond)

			if latency < 1000 {
				cmd.LastCommandStatus = "success"
				cmd.LastAckStatus = "acknowledged"
			} else {
				cmd.LastCommandStatus = "delayed"
				cmd.LastAckStatus = "delayed"
				cmd.DelayedCommandsLast24h = ClampInt(cmd.DelayedCommandsLast24h+1, 0, 50)
			}
		} else {
			cmd.LastCommandStatus = "failed"
			cmd.LastAckStatus = "timeout"
			cmd.LastCommandLatencyMs = 30000
			cmd.LastCommandExecuteTime = nil
			cmd.LastCommandResponseTime = now.Add(30 * time.Second)
			cmd.FailedCommandsLast24h = ClampInt(cmd.FailedCommandsLast24h+1, 0, 50)
		}
	}

	// Slowly decay 24h counters
	if Chance(0.05) {
		cmd.FailedCommandsLast24h = ClampInt(cmd.FailedCommandsLast24h-1, 0, 50)
	}
	if Chance(0.05) {
		cmd.DelayedCommandsLast24h = ClampInt(cmd.DelayedCommandsLast24h-1, 0, 50)
	}
}

// ApplyCybersecurityConstraints randomly generates security events.
func ApplyCybersecurityConstraints(t *models.Telemetry) {
	cs := &t.Cybersecurity

	if Chance(0.02) {
		cs.RecentSecurityEventCount++
		eventType := RandomChoice(securityEventTypes)
		cs.LastSecurityEventType = &eventType
		cs.HighestSecuritySeverity = WeightedChoice(
			[]string{"low", "medium", "high", "critical"},
			[]float64{0.5, 0.3, 0.15, 0.05},
		)
	}

	// Events age out
	if cs.RecentSecurityEventCount > 0 && Chance(0.1) {
		cs.RecentSecurityEventCount = ClampInt(cs.RecentSecurityEventCount-1, 0, 100)
		if cs.RecentSecurityEventCount == 0 {
			cs.HighestSecuritySeverity = "none"
			cs.LastSecurityEventType = nil
		}
	}
}

// ApplyCloudMetricsConstraints updates cloud-side latency/health.
func ApplyCloudMetricsConstraints(t *models.Telemetry) {
	cm := &t.CloudServiceMetrics

	cm.IngestionLatencyMs = RoundTo(GaussianDrift(cm.IngestionLatencyMs, 30, 800, 30), 0)
	cm.ProcessingLatencyMs = RoundTo(GaussianDrift(cm.ProcessingLatencyMs, 50, 1500, 50), 0)
	cm.MessageLossRatePercent = RoundTo(Clamp(GaussianDrift(cm.MessageLossRatePercent, 0, 5, 0.1), 0, 5), 2)

	totalLatency := cm.IngestionLatencyMs + cm.ProcessingLatencyMs
	switch {
	case totalLatency < 500 && cm.MessageLossRatePercent < 1:
		cm.ServiceHealth = "healthy"
	case totalLatency < 1500 && cm.MessageLossRatePercent < 3:
		cm.ServiceHealth = "degraded"
	default:
		cm.ServiceHealth = "unhealthy"
	}
}

// ApplyMobileAppConstraints simulates mobile app interactions.
func ApplyMobileAppConstraints(t *models.Telemetry) {
	app := &t.MobileApp

	if Chance(0.06) {
		app.LastAppEventType = RandomChoice(appEventTypes)
		if t.Connectivity.ConnectionState == "connected" {
			app.LastAppEventStatus = WeightedChoice(
				[]string{"success", "initiated", "pending"},
				[]float64{0.7, 0.2, 0.1},
			)
		} else {
			app.LastAppEventStatus = WeightedChoice(
				[]string{"failed", "timeout", "initiated"},
				[]float64{0.5, 0.3, 0.2},
			)
			app.FailedAppAttemptsLast24h = ClampInt(app.FailedAppAttemptsLast24h+1, 0, 50)
		}
		if app.LastAppEventStatus == "failed" || app.LastAppEventStatus == "timeout" {
			app.RepeatedFeatureAttempts = ClampInt(app.RepeatedFeatureAttempts+1, 0, 20)
		}
	}

	if Chance(0.03) {
		app.FailedAppAttemptsLast24h = ClampInt(app.FailedAppAttemptsLast24h-1, 0, 50)
		app.RepeatedFeatureAttempts = ClampInt(app.RepeatedFeatureAttempts-1, 0, 20)
	}
}

// ApplyLocationTripConstraints updates GPS and trip data.
func ApplyLocationTripConstraints(t *models.Telemetry, drivingMode string) {
	loc := &t.LocationTrip

	if drivingMode == "driving" {
		if t.UserConsent.LocationSharingConsent {
			loc.GPSAvailable = true
			if loc.Latitude == nil {
				lat := 8.0 + rand.Float64()*28  // India latitude range
				lon := 68.0 + rand.Float64()*30 // India longitude range
				loc.Latitude = &lat
				loc.Longitude = &lon
			} else {
				lat := *loc.Latitude + (rand.Float64()-0.5)*0.01
				lon := *loc.Longitude + (rand.Float64()-0.5)*0.01
				loc.Latitude = &lat
				loc.Longitude = &lon
			}
		} else {
			loc.GPSAvailable = false
			loc.Latitude = nil
			loc.Longitude = nil
		}

		if loc.ActiveTripID == nil {
			tripID := fmt.Sprintf("TRIP_%05d", rand.Intn(99999))
			loc.ActiveTripID = &tripID
			loc.LastTripDistanceKm = 0
			loc.LastTripDurationMinutes = 0
		}
		loc.LastTripDistanceKm = RoundTo(loc.LastTripDistanceKm+t.DrivingState.SpeedKmph/720, 1) // 5s tick → /720
		loc.LastTripDurationMinutes = RoundTo(loc.LastTripDurationMinutes+5.0/60.0, 1)

	} else {
		if loc.ActiveTripID != nil {
			loc.ActiveTripID = nil
		}
		// GPS can go unavailable when parked
		if Chance(0.3) {
			loc.GPSAvailable = false
			loc.Latitude = nil
			loc.Longitude = nil
		}
	}
}

// ApplyDataQualityConstraints computes data quality metrics.
func ApplyDataQualityConstraints(t *models.Telemetry) {
	dq := &t.DataQuality

	// Missing fields based on connectivity
	dq.MissingFields = []string{}
	if t.Connectivity.ConnectionState == "disconnected" {
		possibleMissing := []string{"networkType", "signalStrength", "gpsCoordinates", "ecuHeartbeat"}
		for _, f := range possibleMissing {
			if Chance(0.3) {
				dq.MissingFields = append(dq.MissingFields, f)
			}
		}
	} else if t.Connectivity.ConnectionState == "unstable" {
		if Chance(0.2) {
			dq.MissingFields = append(dq.MissingFields, RandomChoice([]string{"networkType", "gpsCoordinates"}))
		}
	}

	totalFields := 50.0
	dq.Completeness = RoundTo(Clamp(1.0-float64(len(dq.MissingFields))/totalFields, 0.7, 1.0), 2)
	dq.Accuracy = RoundTo(Drift(dq.Accuracy, 0.8, 1.0, 0.02), 2)
	dq.AnomalyCount = len(dq.MissingFields) + t.Diagnostics.ActiveDTCCount
}

// ApplyFailureReasonsConstraints generates failure reasons from state.
func ApplyFailureReasonsConstraints(t *models.Telemetry) {
	t.FailureReasons = []models.FailureReason{}

	if t.ECUHealth.LastEcuHeartbeatAgeSeconds > 300 {
		t.FailureReasons = append(t.FailureReasons, models.FailureReason{
			ErrorCode:         "STALE_HEARTBEAT",
			Message:           "No recent heartbeat received from vehicle",
			AffectedComponent: "TCU",
			Severity:          "high",
		})
	}
	if t.Connectivity.ConnectionState == "disconnected" {
		t.FailureReasons = append(t.FailureReasons, models.FailureReason{
			ErrorCode:         "CONN_LOST",
			Message:           "Vehicle connectivity lost",
			AffectedComponent: "Connectivity",
			Severity:          "high",
		})
	}
	if t.VehicleHealth.TemperatureCelsius > 100 {
		t.FailureReasons = append(t.FailureReasons, models.FailureReason{
			ErrorCode:         "ENGINE_OVERHEAT",
			Message:           "Engine temperature exceeding safe threshold",
			AffectedComponent: "Engine",
			Severity:          "critical",
		})
	}
	if t.BatteryCharging.BatteryLevel < 10 {
		t.FailureReasons = append(t.FailureReasons, models.FailureReason{
			ErrorCode:         "LOW_BATTERY",
			Message:           "Battery level critically low",
			AffectedComponent: "Battery",
			Severity:          "high",
		})
	}
	if t.BatteryCharging.BatteryTemperatureCelsius > 50 {
		t.FailureReasons = append(t.FailureReasons, models.FailureReason{
			ErrorCode:         "BATTERY_OVERHEAT",
			Message:           "Battery temperature exceeding safe range",
			AffectedComponent: "Battery",
			Severity:          "critical",
		})
	}
	if t.CloudServiceMetrics.ServiceHealth == "unhealthy" {
		t.FailureReasons = append(t.FailureReasons, models.FailureReason{
			ErrorCode:         "CLOUD_DEGRADED",
			Message:           "Cloud service processing degraded",
			AffectedComponent: "CloudPlatform",
			Severity:          "medium",
		})
	}

	for _, ota := range t.OTA.OTAErrorCodes {
		t.FailureReasons = append(t.FailureReasons, models.FailureReason{
			ErrorCode:         ota,
			Message:           "OTA update error: " + ota,
			AffectedComponent: "OTA",
			Severity:          "medium",
		})
	}
}

// ApplyTimingConstraints updates timing and correlation data.
func ApplyTimingConstraints(t *models.Telemetry) {
	tc := &t.TimingAndCorrelation
	now := time.Now()

	tc.LastEventTime = now
	ingestionDelay := time.Duration(t.CloudServiceMetrics.IngestionLatencyMs) * time.Millisecond
	processingDelay := time.Duration(t.CloudServiceMetrics.ProcessingLatencyMs) * time.Millisecond

	tc.LastIngestionTime = now.Add(ingestionDelay)
	tc.LastProcessingTime = tc.LastIngestionTime.Add(processingDelay)
	tc.LastSequenceNumber++
	tc.LastCorrelationID = fmt.Sprintf("CORR_%s_%06d", t.VIN, tc.LastSequenceNumber)
	tc.LastTraceID = fmt.Sprintf("TRACE_%06d", rand.Intn(999999))

	t.UpdatedAt = tc.LastProcessingTime
}

// ApplyAllConstraints runs all constraint functions in the correct dependency order.
func ApplyAllConstraints(t *models.Telemetry, drivingMode string) {
	ApplyConnectivityConstraints(t, drivingMode)
	ApplyDrivingConstraints(t, drivingMode)
	ApplyBatteryConstraints(t, drivingMode)
	ApplyVehicleHealthConstraints(t, drivingMode)
	ApplyECUConstraints(t, drivingMode)
	ApplyDiagnosticsConstraints(t)
	ApplyOTAConstraints(t, drivingMode)
	ApplyCommandLifecycleConstraints(t)
	ApplyCybersecurityConstraints(t)
	ApplyCloudMetricsConstraints(t)
	ApplyMobileAppConstraints(t)
	ApplyLocationTripConstraints(t, drivingMode)
	ApplyDataQualityConstraints(t)
	ApplyFailureReasonsConstraints(t)
	ApplyTimingConstraints(t)
}

// ComputeTargetDrivingMode determines driving mode transitions with realistic probabilities.
func ComputeTargetDrivingMode(current string, batteryLevel float64) string {
	transitions := map[string][]string{
		"parked":   {"parked", "idle", "driving", "charging"},
		"idle":     {"idle", "parked", "driving"},
		"driving":  {"driving", "idle", "parked"},
		"charging": {"charging", "parked"},
	}

	var weights []float64
	switch current {
	case "parked":
		weights = []float64{0.6, 0.15, 0.15, 0.1}
		if batteryLevel < 20 {
			weights = []float64{0.3, 0.05, 0.05, 0.6} // prefer charging
		}
	case "idle":
		weights = []float64{0.5, 0.2, 0.3}
	case "driving":
		weights = []float64{0.7, 0.15, 0.15}
		if batteryLevel < 10 {
			weights = []float64{0.1, 0.3, 0.6} // must stop
		}
	case "charging":
		weights = []float64{0.8, 0.2}
		if batteryLevel >= 95 {
			weights = []float64{0.2, 0.8} // done charging
		}
	default:
		return "parked"
	}

	choices := transitions[current]
	if len(choices) != len(weights) {
		return current
	}

	return WeightedChoice(choices, weights)
}

// ComputeVehicleHealthScore is a helper to recompute health score from raw values.
func ComputeVehicleHealthScore(fuel, coolant, oil, temp float64, dtcCount int) int {
	score := int((fuel + coolant + oil) / 3.0)
	if temp > 95 {
		score -= int((temp - 95) * 2)
	}
	score -= dtcCount * 5
	return ClampInt(score, 0, 100)
}

// InitialLatitude returns a reasonable starting latitude for an Indian region.
func InitialLatitude(region string) float64 {
	switch region {
	case "IN-North":
		return 28.5 + rand.Float64()*2
	case "IN-South":
		return 12.5 + rand.Float64()*2
	case "IN-East":
		return 22.5 + rand.Float64()*2
	case "IN-West":
		return 19.0 + rand.Float64()*2
	default:
		return 20.0 + rand.Float64()*10
	}
}

// InitialLongitude returns a reasonable starting longitude for an Indian region.
func InitialLongitude(region string) float64 {
	switch region {
	case "IN-North":
		return 77.0 + rand.Float64()*2
	case "IN-South":
		return 77.5 + rand.Float64()*3
	case "IN-East":
		return 87.0 + rand.Float64()*2
	case "IN-West":
		return 72.5 + rand.Float64()*2
	default:
		return 75.0 + rand.Float64()*10
	}
}

// RegionAmbientTemp returns a plausible ambient temperature for a region.
func RegionAmbientTemp(region string) float64 {
	switch region {
	case "IN-North":
		return 35 + rand.Float64()*10
	case "IN-South":
		return 28 + rand.Float64()*8
	case "IN-East":
		return 30 + rand.Float64()*8
	case "IN-West":
		return 32 + rand.Float64()*10
	default:
		return 30 + rand.Float64()*10
	}
}

func AbsFloat(v float64) float64 {
	return math.Abs(v)
}
