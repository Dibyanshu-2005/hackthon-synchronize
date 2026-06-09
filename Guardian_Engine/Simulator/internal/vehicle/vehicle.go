package vehicle

import (
	"fmt"
	"math/rand"
	"time"
	"vehicle-telemetry-simulator/internal/generators"
	"vehicle-telemetry-simulator/internal/models"
)

// Vehicle represents a single simulated vehicle with mutable state.
type Vehicle struct {
	Config      models.VehicleConfig
	DrivingMode string
	Telemetry   models.Telemetry
	tickCount   int
}

// NewVehicle creates a vehicle with a realistic initial telemetry state.
func NewVehicle(cfg models.VehicleConfig) *Vehicle {
	now := time.Now()
	drivingMode := cfg.InitialState
	if drivingMode == "" {
		drivingMode = "parked"
	}

	batteryLevel := 40.0 + rand.Float64()*55 // 40-95%
	fuelLevel := 30.0 + rand.Float64()*60
	coolant := 70.0 + rand.Float64()*25
	oil := 65.0 + rand.Float64()*30
	ambientTemp := generators.RegionAmbientTemp(cfg.Region)

	t := models.Telemetry{
		VIN:    cfg.VIN,
		Model:  cfg.Model,
		Region: cfg.Region,
		VehicleHealth: models.VehicleHealth{
			OverallStatus:       "healthy",
			EngineStatus:        "off",
			TemperatureCelsius:  generators.RoundTo(ambientTemp, 1),
			FuelLevelPercent:    generators.RoundTo(fuelLevel, 1),
			CoolantLevelPercent: generators.RoundTo(coolant, 1),
			OilLevelPercent:     generators.RoundTo(oil, 1),
			VehicleHealthScore:  generators.ComputeVehicleHealthScore(fuelLevel, coolant, oil, ambientTemp, 0),
		},
		ECUHealth: models.ECUHealth{
			PrimaryEcuID:               "TCU_01",
			PrimaryEcuStatus:           "healthy",
			TCUCpuUsagePercent:         generators.RoundTo(10+rand.Float64()*30, 1),
			TCUMemoryUsagePercent:      generators.RoundTo(20+rand.Float64()*30, 1),
			LastEcuHeartbeatAgeSeconds: rand.Intn(30),
		},
		DrivingState: models.DrivingState{
			SpeedKmph:            0,
			AccelerationMps2:     0,
			Gear:                 "park",
			BrakeStatus:          "engaged",
			SteeringAngleDegrees: 0,
			DrivingMode:          "parked",
		},
		BatteryCharging: models.BatteryCharging{
			BatteryLevel:              generators.RoundTo(batteryLevel, 1),
			RangeKm:                   generators.RoundTo(batteryLevel*4.2, 0),
			ChargingStatus:            "not_charging",
			ChargingType:              "none",
			ChargingPowerKw:           0,
			BatteryTemperatureCelsius: generators.RoundTo(ambientTemp-2+rand.Float64()*4, 1),
		},
		Diagnostics: models.Diagnostics{
			ActiveDTCCount:     0,
			HighestDTCSeverity: "none",
			DTCCodes:           []string{},
		},
		OTA: models.OTA{
			UpdateID:            fmt.Sprintf("OTA_%d_%02d_%03d", now.Year(), now.Month(), rand.Intn(999)+1),
			OTAStatus:           "not_started",
			OTAProgressPercent:  0,
			TargetVersion:       fmt.Sprintf("TCU-%d.%d.%d", 3+rand.Intn(2), rand.Intn(10), rand.Intn(10)),
			OTAPackageAvailable: false,
			OTAErrorCodes:       []string{},
		},
		SoftwareInventory: models.SoftwareInventory{
			ComponentsOutdatedCount:     rand.Intn(3),
			CriticalComponentsOutdated:  []string{},
			LastSoftwareInventoryUpdate: now.Add(-time.Duration(rand.Intn(72)) * time.Hour),
		},
		CommandLifecycle: models.CommandLifecycle{
			LastCommandID:           fmt.Sprintf("CMD_%05d", rand.Intn(99999)),
			LastCommandType:         "remote_lock",
			LastCommandStatus:       "success",
			LastCommandIssueTime:    now.Add(-time.Duration(rand.Intn(3600)) * time.Second),
			LastCommandExecuteTime:  nil,
			LastCommandResponseTime: now.Add(-time.Duration(rand.Intn(3600)) * time.Second),
			LastCommandLatencyMs:    200 + rand.Intn(1800),
			LastAckStatus:           "acknowledged",
			FailedCommandsLast24h:   rand.Intn(5),
			DelayedCommandsLast24h:  rand.Intn(3),
		},
		Connectivity: models.Connectivity{
			NetworkType:             generators.WeightedChoice([]string{"5G", "4G", "3G", "2G"}, []float64{0.15, 0.55, 0.2, 0.1}),
			SignalStrengthPercent:   generators.RoundTo(40+rand.Float64()*55, 0),
			LatencyMs:               generators.RoundTo(50+rand.Float64()*400, 0),
			ConnectionState:         "connected",
			LastConnectedTime:       now,
			LastHeartbeatMinutes:    float64(rand.Intn(5)),
			ReconnectCountLast15Min: rand.Intn(3),
			DeviceTwinAgeMinutes:    float64(rand.Intn(10)),
		},
		Cybersecurity: models.Cybersecurity{
			RecentSecurityEventCount: 0,
			HighestSecuritySeverity:  "none",
			LastSecurityEventType:    nil,
		},
		CloudServiceMetrics: models.CloudServiceMetrics{
			IngestionLatencyMs:     generators.RoundTo(80+rand.Float64()*150, 0),
			ProcessingLatencyMs:    generators.RoundTo(100+rand.Float64()*300, 0),
			MessageLossRatePercent: generators.RoundTo(rand.Float64()*0.5, 2),
			ServiceHealth:          "healthy",
		},
		MobileApp: models.MobileApp{
			LastAppEventType:         "vehicle_status_refresh",
			LastAppEventStatus:       "success",
			FailedAppAttemptsLast24h: rand.Intn(3),
			RepeatedFeatureAttempts:  rand.Intn(2),
		},
		UserConsent: models.UserConsent{
			DataSharingConsent:     true,
			LocationSharingConsent: generators.Chance(0.7),
			AnalyticsConsent:       generators.Chance(0.8),
			LastUpdated:            now.Add(-time.Duration(rand.Intn(720)) * time.Hour),
		},
		LocationTrip: models.LocationTrip{
			GPSAvailable:            false,
			Latitude:                nil,
			Longitude:               nil,
			ActiveTripID:            nil,
			LastTripDistanceKm:      generators.RoundTo(5+rand.Float64()*50, 1),
			LastTripDurationMinutes: generators.RoundTo(10+rand.Float64()*90, 1),
		},
		DataQuality: models.DataQuality{
			Completeness:  0.95,
			Accuracy:      0.92,
			AnomalyCount:  0,
			MissingFields: []string{},
		},
		FailureReasons: []models.FailureReason{},
		TimingAndCorrelation: models.TimingAndCorrelation{
			LastEventTime:      now,
			LastIngestionTime:  now,
			LastProcessingTime: now,
			LastSequenceNumber: rand.Intn(1000),
			LastCorrelationID:  fmt.Sprintf("CORR_%s_%06d", cfg.VIN, rand.Intn(999999)),
			LastTraceID:        fmt.Sprintf("TRACE_%06d", rand.Intn(999999)),
		},
		UpdatedAt: now,
	}

	// If software is outdated, add critical components
	if t.SoftwareInventory.ComponentsOutdatedCount > 0 {
		outdated := []string{"TCU_FW", "BCM_FW", "ADAS_FW", "IVI_FW"}
		for i := 0; i < t.SoftwareInventory.ComponentsOutdatedCount && i < len(outdated); i++ {
			t.SoftwareInventory.CriticalComponentsOutdated = append(t.SoftwareInventory.CriticalComponentsOutdated, outdated[i])
		}
	}

	v := &Vehicle{
		Config:      cfg,
		DrivingMode: drivingMode,
		Telemetry:   t,
	}

	// Apply initial driving state
	generators.ApplyDrivingConstraints(&v.Telemetry, drivingMode)
	if drivingMode == "charging" {
		v.Telemetry.BatteryCharging.ChargingStatus = "charging"
		v.Telemetry.BatteryCharging.ChargingType = generators.WeightedChoice([]string{"ac_slow", "ac_fast", "dc_fast"}, []float64{0.4, 0.35, 0.25})
	}

	return v
}

// Tick advances the vehicle state by one simulation step.
func (v *Vehicle) Tick() models.Telemetry {
	v.tickCount++

	// Every N ticks, consider a state transition
	if v.tickCount%3 == 0 {
		v.DrivingMode = generators.ComputeTargetDrivingMode(v.DrivingMode, v.Telemetry.BatteryCharging.BatteryLevel)
	}

	// Force stop driving if battery dead
	if v.Telemetry.BatteryCharging.BatteryLevel <= 1 && v.DrivingMode == "driving" {
		v.DrivingMode = "parked"
	}

	generators.ApplyAllConstraints(&v.Telemetry, v.DrivingMode)

	return v.Telemetry
}
