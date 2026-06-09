package output

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sync"

	"vehicle-telemetry-simulator/internal/models"

	"github.com/gorilla/websocket"
)

// Handler defines the interface for telemetry output.
type Handler interface {
	Send(telemetry models.Telemetry) error
	Close() error
}

// --- Console Output ---

type ConsoleHandler struct{}

func NewConsoleHandler() *ConsoleHandler {
	return &ConsoleHandler{}
}

func (c *ConsoleHandler) Send(t models.Telemetry) error {
	data, err := json.Marshal(t)
	if err != nil {
		return err
	}
	fmt.Println(string(data))
	return nil
}

func (c *ConsoleHandler) Close() error { return nil }

// --- File Output (JSONL) ---

type FileHandler struct {
	file *os.File
	mu   sync.Mutex
}

func NewFileHandler(path string) (*FileHandler, error) {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("create output dir: %w", err)
	}
	f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return nil, fmt.Errorf("open output file: %w", err)
	}
	return &FileHandler{file: f}, nil
}

func (fh *FileHandler) Send(t models.Telemetry) error {
	data, err := json.Marshal(t)
	if err != nil {
		return err
	}
	fh.mu.Lock()
	defer fh.mu.Unlock()
	_, err = fh.file.Write(append(data, '\n'))
	return err
}

func (fh *FileHandler) Close() error {
	return fh.file.Close()
}

// --- WebSocket Output ---

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all origins for simulator; restrict in production
	},
}

type sseClient struct {
	ch chan []byte
}

type WebSocketHandler struct {
	clients    map[*websocket.Conn]bool
	sseClients map[*sseClient]bool
	mu         sync.RWMutex
	server     *http.Server
}

func NewWebSocketHandler(port int) *WebSocketHandler {
	ws := &WebSocketHandler{
		clients:    make(map[*websocket.Conn]bool),
		sseClients: make(map[*sseClient]bool),
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/ws", ws.handleConnection)
	mux.HandleFunc("/sse", ws.handleSSE)
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprintln(w, `{"status":"ok"}`)
	})
	mux.HandleFunc("/", ws.serveDashboard)

	ws.server = &http.Server{
		Addr:    fmt.Sprintf(":%d", port),
		Handler: mux,
	}

	go func() {
		log.Printf("[WebSocket] Listening on :%d", port)
		if err := ws.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[WebSocket] Server error: %v", err)
		}
	}()

	return ws
}

func (ws *WebSocketHandler) handleConnection(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("[WebSocket] Upgrade error: %v", err)
		return
	}

	ws.mu.Lock()
	ws.clients[conn] = true
	ws.mu.Unlock()

	log.Printf("[WebSocket] Client connected (%d total)", len(ws.clients))

	// Read loop to detect disconnects
	go func() {
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				ws.mu.Lock()
				delete(ws.clients, conn)
				ws.mu.Unlock()
				conn.Close()
				log.Printf("[WebSocket] Client disconnected (%d remaining)", len(ws.clients))
				return
			}
		}
	}()
}

func (ws *WebSocketHandler) Send(t models.Telemetry) error {
	data, err := json.Marshal(t)
	if err != nil {
		return err
	}

	ws.mu.RLock()
	defer ws.mu.RUnlock()

	// Send to WebSocket clients
	for conn := range ws.clients {
		if err := conn.WriteMessage(websocket.TextMessage, data); err != nil {
			log.Printf("[WebSocket] Write error: %v", err)
			conn.Close()
			delete(ws.clients, conn)
		}
	}

	// Send to SSE clients
	for client := range ws.sseClients {
		select {
		case client.ch <- data:
		default:
			// Client too slow, skip
		}
	}

	return nil
}

func (ws *WebSocketHandler) Close() error {
	ws.mu.Lock()
	for conn := range ws.clients {
		conn.Close()
	}
	for client := range ws.sseClients {
		close(client.ch)
	}
	ws.mu.Unlock()
	return ws.server.Close()
}

func (ws *WebSocketHandler) handleSSE(w http.ResponseWriter, r *http.Request) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "SSE not supported", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	client := &sseClient{ch: make(chan []byte, 50)}

	ws.mu.Lock()
	ws.sseClients[client] = true
	ws.mu.Unlock()

	log.Printf("[SSE] Client connected (%d total)", len(ws.sseClients))

	defer func() {
		ws.mu.Lock()
		delete(ws.sseClients, client)
		ws.mu.Unlock()
		log.Printf("[SSE] Client disconnected (%d remaining)", len(ws.sseClients))
	}()

	for {
		select {
		case data, ok := <-client.ch:
			if !ok {
				return
			}
			fmt.Fprintf(w, "data: %s\n\n", data)
			flusher.Flush()
		case <-r.Context().Done():
			return
		}
	}
}

func (ws *WebSocketHandler) serveDashboard(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html")
	fmt.Fprint(w, getDashboardHTML())
}

// --- Multi Output (fan-out to multiple handlers) ---

type MultiHandler struct {
	handlers []Handler
}

func NewMultiHandler(handlers ...Handler) *MultiHandler {
	return &MultiHandler{handlers: handlers}
}

func (m *MultiHandler) Send(t models.Telemetry) error {
	for _, h := range m.handlers {
		if err := h.Send(t); err != nil {
			log.Printf("[MultiOutput] Handler error: %v", err)
		}
	}
	return nil
}

func (m *MultiHandler) Close() error {
	for _, h := range m.handlers {
		h.Close()
	}
	return nil
}
