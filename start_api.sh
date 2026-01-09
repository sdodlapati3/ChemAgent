#!/bin/bash
#
# Start ChemAgent FastAPI server
#
# Usage:
#   ./start_api.sh              # Start on default port 8000
#   ./start_api.sh --port 8080  # Start on custom port
#

# Default configuration
PORT="${CHEMAGENT_PORT:-8000}"
HOST="${CHEMAGENT_HOST:-0.0.0.0}"
RELOAD="--reload"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --no-reload)
            RELOAD=""
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --port PORT       Server port (default: 8000)"
            echo "  --host HOST       Server host (default: 0.0.0.0)"
            echo "  --no-reload       Disable auto-reload"
            echo "  --help            Show this help"
            echo ""
            echo "Environment variables:"
            echo "  CHEMAGENT_PORT            Server port"
            echo "  CHEMAGENT_HOST            Server host"
            echo "  CHEMAGENT_USE_REAL_TOOLS  Use real APIs (default: true)"
            echo "  CHEMAGENT_ENABLE_CACHE    Enable caching (default: true)"
            echo "  CHEMAGENT_CACHE_DIR       Cache directory (default: .cache/chemagent)"
            echo "  CHEMAGENT_CACHE_TTL       Cache TTL in seconds (default: 3600)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Starting ChemAgent API Server..."
echo "Host: $HOST"
echo "Port: $PORT"
echo "API docs: http://$HOST:$PORT/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server with the correct Python environment
crun -p ~/envs/chemagent python -m uvicorn chemagent.api.server:app \
    --host "$HOST" \
    --port "$PORT" \
    $RELOAD \
    --log-level info
