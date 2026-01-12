#!/bin/bash
#SBATCH --job-name=chemagent-api
#SBATCH --output=logs/chemagent-api-%j.out
#SBATCH --error=logs/chemagent-api-%j.err
#SBATCH --time=24:00:00
#SBATCH --partition=cpuspot
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G

# ============================================================================
# ChemAgent API Server - SLURM Job Script
# ============================================================================
# Usage:
#   sbatch scripts/start_server.slurm              # Default port 8000
#   sbatch --export=PORT=8080 scripts/start_server.slurm  # Custom port
#
# To check status:
#   squeue -u $USER
#
# To view logs:
#   tail -f logs/chemagent-api-<jobid>.out
#
# To stop:
#   scancel <jobid>
# ============================================================================

# Configuration
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}
WORKERS=${WORKERS:-4}
ENV_PATH="${HOME}/envs/chemagent"
PROJECT_DIR="${HOME}/ChemAgent"

# Print job info
echo "=============================================="
echo "ChemAgent API Server Starting"
echo "=============================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Time: $(date)"
echo "Port: $PORT"
echo "Host: $HOST"
echo "Workers: $WORKERS"
echo "=============================================="

# Change to project directory
cd "$PROJECT_DIR" || { echo "ERROR: Cannot cd to $PROJECT_DIR"; exit 1; }

# Create logs directory if not exists
mkdir -p logs

# Load Python module
module load python3

# Check if environment exists
if [ ! -d "$ENV_PATH" ]; then
    echo "ERROR: Python environment not found at $ENV_PATH"
    echo "Create it with: python -m venv $ENV_PATH && pip install -e ."
    exit 1
fi

# Export environment variables
export CHEMAGENT_PORT=$PORT
export CHEMAGENT_HOST=$HOST
export CHEMAGENT_USE_REAL_TOOLS=true
export CHEMAGENT_ENABLE_CACHE=true
export CHEMAGENT_ENABLE_LLM=true
export CHEMAGENT_LOG_LEVEL=INFO

# Save connection info for users
CONNECTION_FILE="logs/server_connection.txt"
cat > "$CONNECTION_FILE" << EOF
============================================
ChemAgent Server Connection Info
============================================
Job ID: $SLURM_JOB_ID
Node: $SLURM_NODELIST
URL: http://${SLURM_NODELIST}:${PORT}
Health: http://${SLURM_NODELIST}:${PORT}/health
API Docs: http://${SLURM_NODELIST}:${PORT}/docs
Started: $(date)

To access from your local machine, set up SSH tunnel:
  ssh -L ${PORT}:${SLURM_NODELIST}:${PORT} <username>@<login-node>

Then open in browser:
  http://localhost:${PORT}
============================================
EOF

echo ""
echo "Connection info saved to: $CONNECTION_FILE"
cat "$CONNECTION_FILE"
echo ""

# Start server using crun
echo "Starting uvicorn server..."
crun -p "$ENV_PATH" uvicorn chemagent.api.server:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level info

# This line runs when server stops
echo ""
echo "Server stopped at $(date)"
