#!/bin/bash
# ============================================================================
# ChemAgent Server Management Script (Login Node)
# ============================================================================
# Usage:
#   ./scripts/server.sh start [port]    - Start server on login node
#   ./scripts/server.sh stop            - Stop running server
#   ./scripts/server.sh status          - Check server status
#   ./scripts/server.sh logs            - View server logs
#   ./scripts/server.sh restart [port]  - Restart server
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$LOG_DIR/.server.pid"
LOG_FILE="$LOG_DIR/server.log"
ENV_PATH="${HOME}/envs/chemagent"

cd "$PROJECT_DIR"
mkdir -p "$LOG_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_warn() { echo -e "${YELLOW}⚠${NC} $1"; }

get_pid() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "$PID"
            return 0
        fi
    fi
    pgrep -f "uvicorn chemagent.api.server" 2>/dev/null | head -1
}

start_server() {
    PORT=${1:-8000}
    
    EXISTING_PID=$(get_pid)
    if [ -n "$EXISTING_PID" ]; then
        print_error "Server already running (PID: $EXISTING_PID)"
        echo "Use './scripts/server.sh stop' to stop it first"
        exit 1
    fi
    
    print_info "Starting ChemAgent server on port $PORT..."
    
    module load python3 2>/dev/null || true
    
    if [ ! -d "$ENV_PATH" ]; then
        print_error "Python environment not found: $ENV_PATH"
        exit 1
    fi
    
    export CHEMAGENT_PORT=$PORT
    export CHEMAGENT_HOST=0.0.0.0
    export CHEMAGENT_USE_REAL_TOOLS=true
    export CHEMAGENT_ENABLE_CACHE=true
    
    nohup crun -p "$ENV_PATH" uvicorn chemagent.api.server:app \
        --host 0.0.0.0 \
        --port "$PORT" \
        --log-level info \
        >> "$LOG_FILE" 2>&1 &
    
    SERVER_PID=$!
    echo "$SERVER_PID" > "$PID_FILE"
    
    print_info "Waiting for server to start..."
    for i in {1..15}; do
        sleep 1
        if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
            echo ""
            print_status "Server started successfully!"
            echo ""
            echo "=============================================="
            echo -e "${GREEN}ChemAgent Server Running${NC}"
            echo "=============================================="
            echo "PID:      $SERVER_PID"
            echo "Port:     $PORT"
            echo "Host:     $(hostname)"
            echo ""
            echo -e "${BLUE}Access URLs:${NC}"
            echo "  Frontend: http://$(hostname):$PORT/"
            echo "  API Docs: http://$(hostname):$PORT/docs"
            echo "  Health:   http://$(hostname):$PORT/health"
            echo ""
            echo -e "${YELLOW}From local machine (SSH tunnel):${NC}"
            echo "  ssh -L $PORT:localhost:$PORT $USER@$(hostname -f)"
            echo "  Then open: http://localhost:$PORT/"
            echo "=============================================="
            return 0
        fi
        echo -n "."
    done
    
    echo ""
    print_error "Server failed to start. Check logs:"
    tail -20 "$LOG_FILE"
    exit 1
}

stop_server() {
    PID=$(get_pid)
    if [ -z "$PID" ]; then
        print_info "No running server found"
        rm -f "$PID_FILE"
        return 0
    fi
    
    print_info "Stopping server (PID: $PID)..."
    kill "$PID" 2>/dev/null
    
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            print_status "Server stopped"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done
    
    kill -9 "$PID" 2>/dev/null
    rm -f "$PID_FILE"
    print_status "Server force stopped"
}

show_status() {
    PID=$(get_pid)
    if [ -n "$PID" ]; then
        PORT=$(ss -tlnp 2>/dev/null | grep "$PID" | awk '{print $4}' | grep -oP ':\K\d+' | head -1)
        PORT=${PORT:-8000}
        
        print_status "Server is running"
        echo "  PID:  $PID"
        echo "  Port: $PORT"
        echo "  Host: $(hostname)"
        echo "  URL:  http://$(hostname):$PORT/"
        
        if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
            print_status "Health check: OK"
        else
            print_warn "Health check: FAILED"
        fi
    else
        print_info "Server is not running"
    fi
}

show_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        print_error "No log file found: $LOG_FILE"
    fi
}

case "${1:-help}" in
    start)
        start_server "$2"
        ;;
    stop)
        stop_server
        ;;
    restart)
        stop_server
        sleep 2
        start_server "$2"
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "ChemAgent Server Management"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs} [port]"
        echo ""
        echo "Commands:"
        echo "  start [port]   Start server (default port: 8000)"
        echo "  stop           Stop running server"
        echo "  restart [port] Restart server"
        echo "  status         Show server status"
        echo "  logs           Tail server logs"
        ;;
esac
