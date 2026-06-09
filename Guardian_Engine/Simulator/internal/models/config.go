package models

type FleetConfig struct {
	SimulationIntervalMs int             `json:"simulationIntervalMs"`
	OutputMode           string          `json:"outputMode"`
	WebsocketPort        int             `json:"websocketPort"`
	OutputFilePath       string          `json:"outputFilePath"`
	Vehicles             []VehicleConfig `json:"vehicles"`
}

type VehicleConfig struct {
	VIN          string `json:"vin"`
	Model        string `json:"model"`
	Region       string `json:"region"`
	InitialState string `json:"initialState"`
}
