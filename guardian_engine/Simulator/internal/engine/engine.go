package engine

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"sync"
	"time"
	"vehicle-telemetry-simulator/internal/models"
	"vehicle-telemetry-simulator/internal/output"
	"vehicle-telemetry-simulator/internal/vehicle"
)

// Engine orchestrates the fleet simulation.
type Engine struct {
	config   models.FleetConfig
	vehicles []*vehicle.Vehicle
	output   output.Handler
	stopCh   chan struct{}
	wg       sync.WaitGroup
}

// New creates a simulator engine from a fleet config file path.
func New(configPath string, outputOverride string) (*Engine, error) {
	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, fmt.Errorf("read config: %w", err)
	}

	var cfg models.FleetConfig
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}

	if outputOverride != "" {
		cfg.OutputMode = outputOverride
	}

	// Initialize vehicles
	vehicles := make([]*vehicle.Vehicle, len(cfg.Vehicles))
	for i, vc := range cfg.Vehicles {
		vehicles[i] = vehicle.NewVehicle(vc)
		log.Printf("[Engine] Initialized vehicle %s (%s) in %s — state: %s",
			vc.VIN, vc.Model, vc.Region, vc.InitialState)
	}

	// Initialize output handler
	var handler output.Handler
	switch cfg.OutputMode {
	case "console":
		handler = output.NewConsoleHandler()
	case "file":
		handler, err = output.NewFileHandler(cfg.OutputFilePath)
		if err != nil {
			return nil, fmt.Errorf("init file output: %w", err)
		}
	case "websocket":
		handler = output.NewWebSocketHandler(cfg.WebsocketPort)
	case "console+websocket":
		console := output.NewConsoleHandler()
		ws := output.NewWebSocketHandler(cfg.WebsocketPort)
		handler = output.NewMultiHandler(console, ws)
	case "console+file":
		console := output.NewConsoleHandler()
		fh, err := output.NewFileHandler(cfg.OutputFilePath)
		if err != nil {
			return nil, fmt.Errorf("init file output: %w", err)
		}
		handler = output.NewMultiHandler(console, fh)
	default:
		handler = output.NewConsoleHandler()
	}

	return &Engine{
		config:   cfg,
		vehicles: vehicles,
		output:   handler,
		stopCh:   make(chan struct{}),
	}, nil
}

// Start begins the simulation loop.
func (e *Engine) Start() {
	interval := time.Duration(e.config.SimulationIntervalMs) * time.Millisecond
	log.Printf("[Engine] Starting simulation — %d vehicles, interval %v, output: %s",
		len(e.vehicles), interval, e.config.OutputMode)

	e.wg.Add(1)
	go func() {
		defer e.wg.Done()
		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		// Emit initial state immediately
		e.tickAll()

		for {
			select {
			case <-ticker.C:
				e.tickAll()
			case <-e.stopCh:
				log.Println("[Engine] Simulation stopped")
				return
			}
		}
	}()
}

func (e *Engine) tickAll() {
	for _, v := range e.vehicles {
		telemetry := v.Tick()
		if err := e.output.Send(telemetry); err != nil {
			log.Printf("[Engine] Output error for %s: %v", v.Config.VIN, err)
		}
	}
}

// Stop gracefully shuts down the engine.
func (e *Engine) Stop() {
	close(e.stopCh)
	e.wg.Wait()
	e.output.Close()
	log.Println("[Engine] Shutdown complete")
}
