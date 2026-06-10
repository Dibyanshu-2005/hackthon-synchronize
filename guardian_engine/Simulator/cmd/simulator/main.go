package main

import (
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"
	"vehicle-telemetry-simulator/internal/engine"
)

func main() {
	configPath := flag.String("config", "config/fleet.json", "Path to fleet configuration file")
	outputMode := flag.String("output", "", "Output mode override: console, file, websocket, console+websocket, console+file")
	flag.Parse()

	eng, err := engine.New(*configPath, *outputMode)
	if err != nil {
		log.Fatalf("Failed to initialize engine: %v", err)
	}

	eng.Start()

	// Wait for interrupt signal for graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	log.Println("Received shutdown signal...")
	eng.Stop()
}
