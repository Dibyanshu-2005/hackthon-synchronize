package models

import "time"

type Telemetry struct {
	VIN                  string               `json:"vin"`
	Model                string               `json:"model"`
	Region               string               `json:"region"`
	VehicleHealth        VehicleHealth        `json:"vehicleHealth"`
	ECUHealth            ECUHealth            `json:"ecuHealth"`
	DrivingState         DrivingState         `json:"drivingState"`
	BatteryCharging      BatteryCharging      `json:"batteryCharging"`
	Diagnostics          Diagnostics          `json:"diagnostics"`
	OTA                  OTA                  `json:"ota"`
	SoftwareInventory    SoftwareInventory    `json:"softwareInventory"`
	CommandLifecycle     CommandLifecycle     `json:"commandLifecycle"`
	Connectivity         Connectivity         `json:"connectivity"`
	Cybersecurity        Cybersecurity        `json:"cybersecurity"`
	CloudServiceMetrics  CloudServiceMetrics  `json:"cloudServiceMetrics"`
	MobileApp            MobileApp            `json:"mobileApp"`
	UserConsent          UserConsent          `json:"userConsent"`
	LocationTrip         LocationTrip         `json:"locationTrip"`
	DataQuality          DataQuality          `json:"dataQuality"`
	FailureReasons       []FailureReason      `json:"failureReasons"`
	TimingAndCorrelation TimingAndCorrelation `json:"timingAndCorrelation"`
	UpdatedAt            time.Time            `json:"updatedAt"`
}

type VehicleHealth struct {
	OverallStatus       string  `json:"overallStatus"`
	EngineStatus        string  `json:"engineStatus"`
	TemperatureCelsius  float64 `json:"temperatureCelsius"`
	FuelLevelPercent    float64 `json:"fuelLevelPercent"`
	CoolantLevelPercent float64 `json:"coolantLevelPercent"`
	OilLevelPercent     float64 `json:"oilLevelPercent"`
	VehicleHealthScore  int     `json:"vehicleHealthScore"`
}

type ECUHealth struct {
	PrimaryEcuID               string  `json:"primaryEcuId"`
	PrimaryEcuStatus           string  `json:"primaryEcuStatus"`
	TCUCpuUsagePercent         float64 `json:"tcuCpuUsagePercent"`
	TCUMemoryUsagePercent      float64 `json:"tcuMemoryUsagePercent"`
	LastEcuHeartbeatAgeSeconds int     `json:"lastEcuHeartbeatAgeSeconds"`
}

type DrivingState struct {
	SpeedKmph            float64 `json:"speedKmph"`
	AccelerationMps2     float64 `json:"accelerationMps2"`
	Gear                 string  `json:"gear"`
	BrakeStatus          string  `json:"brakeStatus"`
	SteeringAngleDegrees float64 `json:"steeringAngleDegrees"`
	DrivingMode          string  `json:"drivingMode"`
}

type BatteryCharging struct {
	BatteryLevel              float64 `json:"batteryLevel"`
	RangeKm                   float64 `json:"rangeKm"`
	ChargingStatus            string  `json:"chargingStatus"`
	ChargingType              string  `json:"chargingType"`
	ChargingPowerKw           float64 `json:"chargingPowerKw"`
	BatteryTemperatureCelsius float64 `json:"batteryTemperatureCelsius"`
}

type Diagnostics struct {
	ActiveDTCCount     int      `json:"activeDtcCount"`
	HighestDTCSeverity string   `json:"highestDtcSeverity"`
	DTCCodes           []string `json:"dtcCodes"`
}

type OTA struct {
	UpdateID            string   `json:"updateId"`
	OTAStatus           string   `json:"otaStatus"`
	OTAProgressPercent  float64  `json:"otaProgressPercent"`
	TargetVersion       string   `json:"targetVersion"`
	OTAPackageAvailable bool     `json:"otaPackageAvailable"`
	OTAErrorCodes       []string `json:"otaErrorCodes"`
}

type SoftwareInventory struct {
	ComponentsOutdatedCount     int       `json:"componentsOutdatedCount"`
	CriticalComponentsOutdated  []string  `json:"criticalComponentsOutdated"`
	LastSoftwareInventoryUpdate time.Time `json:"lastSoftwareInventoryUpdate"`
}

type CommandLifecycle struct {
	LastCommandID           string     `json:"lastCommandId"`
	LastCommandType         string     `json:"lastCommandType"`
	LastCommandStatus       string     `json:"lastCommandStatus"`
	LastCommandIssueTime    time.Time  `json:"lastCommandIssueTime"`
	LastCommandExecuteTime  *time.Time `json:"lastCommandExecuteTime"`
	LastCommandResponseTime time.Time  `json:"lastCommandResponseTime"`
	LastCommandLatencyMs    int        `json:"lastCommandLatencyMs"`
	LastAckStatus           string     `json:"lastAckStatus"`
	FailedCommandsLast24h   int        `json:"failedCommandsLast24h"`
	DelayedCommandsLast24h  int        `json:"delayedCommandsLast24h"`
}

type Connectivity struct {
	NetworkType             string    `json:"networkType"`
	SignalStrengthPercent   float64   `json:"signalStrengthPercent"`
	LatencyMs               float64   `json:"latencyMs"`
	ConnectionState         string    `json:"connectionState"`
	LastConnectedTime       time.Time `json:"lastConnectedTime"`
	LastHeartbeatMinutes    float64   `json:"lastHeartbeatMinutes"`
	ReconnectCountLast15Min int       `json:"reconnectCountLast15Min"`
	DeviceTwinAgeMinutes    float64   `json:"deviceTwinAgeMinutes"`
}

type Cybersecurity struct {
	RecentSecurityEventCount int     `json:"recentSecurityEventCount"`
	HighestSecuritySeverity  string  `json:"highestSecuritySeverity"`
	LastSecurityEventType    *string `json:"lastSecurityEventType"`
}

type CloudServiceMetrics struct {
	IngestionLatencyMs     float64 `json:"ingestionLatencyMs"`
	ProcessingLatencyMs    float64 `json:"processingLatencyMs"`
	MessageLossRatePercent float64 `json:"messageLossRatePercent"`
	ServiceHealth          string  `json:"serviceHealth"`
}

type MobileApp struct {
	LastAppEventType         string `json:"lastAppEventType"`
	LastAppEventStatus       string `json:"lastAppEventStatus"`
	FailedAppAttemptsLast24h int    `json:"failedAppAttemptsLast24h"`
	RepeatedFeatureAttempts  int    `json:"repeatedFeatureAttempts"`
}

type UserConsent struct {
	DataSharingConsent     bool      `json:"dataSharingConsent"`
	LocationSharingConsent bool      `json:"locationSharingConsent"`
	AnalyticsConsent       bool      `json:"analyticsConsent"`
	LastUpdated            time.Time `json:"lastUpdated"`
}

type LocationTrip struct {
	GPSAvailable            bool     `json:"gpsAvailable"`
	Latitude                *float64 `json:"latitude"`
	Longitude               *float64 `json:"longitude"`
	ActiveTripID            *string  `json:"activeTripId"`
	LastTripDistanceKm      float64  `json:"lastTripDistanceKm"`
	LastTripDurationMinutes float64  `json:"lastTripDurationMinutes"`
}

type DataQuality struct {
	Completeness  float64  `json:"completeness"`
	Accuracy      float64  `json:"accuracy"`
	AnomalyCount  int      `json:"anomalyCount"`
	MissingFields []string `json:"missingFields"`
}

type FailureReason struct {
	ErrorCode         string `json:"errorCode"`
	Message           string `json:"message"`
	AffectedComponent string `json:"affectedComponent"`
	Severity          string `json:"severity"`
}

type TimingAndCorrelation struct {
	LastEventTime      time.Time `json:"lastEventTime"`
	LastIngestionTime  time.Time `json:"lastIngestionTime"`
	LastProcessingTime time.Time `json:"lastProcessingTime"`
	LastSequenceNumber int       `json:"lastSequenceNumber"`
	LastCorrelationID  string    `json:"lastCorrelationId"`
	LastTraceID        string    `json:"lastTraceId"`
}
