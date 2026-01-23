#!/usr/bin/env bash
set -euo pipefail

# GitPulse - Start Script
# Starts the GitPulse application and Ollama service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load script helpers
SCRIPT_HELPERS_DIR="${SCRIPT_HELPERS_DIR:-$ROOT_DIR/vendor/script-helpers}"
if [[ -f "$SCRIPT_HELPERS_DIR/helpers.sh" ]]; then
    # shellcheck disable=SC1091
    source "$SCRIPT_HELPERS_DIR/helpers.sh"
    shlib_import logging
else
    log_info() { echo "[INFO] $*"; }
    log_warn() { echo "[WARN] $*"; }
    log_error() { echo "[ERROR] $*"; }
fi

cd "$ROOT_DIR"

# Parse arguments
USE_DOCKER=false
DEV_MODE=false
REBUILD_DOCKER=false

for arg in "$@"; do
    case $arg in
        --docker)
            USE_DOCKER=true
            ;;
        -b|--build)
            REBUILD_DOCKER=true
            ;;
        --dev)
            DEV_MODE=true
            ;;
        --help|-h)
            echo "Usage: $0 [--docker] [--dev] [-b|--build]"
            echo ""
            echo "Options:"
            echo "  --docker    Use Docker Compose to start services"
            echo "  --dev       Start in development mode with auto-reload"
            echo "  -b, --build Rebuild Docker containers before starting"
            exit 0
            ;;
    esac
done

if [[ "$USE_DOCKER" == "true" ]]; then
    log_info "Starting GitPulse with Docker Compose..."

    # Check Docker is available
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Install Docker first."
        exit 1
    fi

    # Start services (using docker compose v2)
    if [[ "$REBUILD_DOCKER" == "true" ]]; then
        docker compose up -d --build
    else
        docker compose up -d
    fi

    log_info "Waiting for services to start..."
    sleep 5

    # Pull model if not already done
    log_info "Ensuring Ollama model is available..."
    docker exec gitpulse-ollama ollama pull codellama:7b 2>/dev/null || true

    log_info "GitPulse is running!"
    echo ""
    echo "  Dashboard: http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/docs"
    echo "  Ollama:    http://localhost:11434"
    echo ""
    echo "To view logs: docker compose logs -f"
    echo "To stop:      ./scripts/stop.sh --docker"

else
    log_info "Starting GitPulse locally..."

    # Check Python venv
    if [[ ! -d "$ROOT_DIR/.venv" ]]; then
        log_info "Creating virtual environment..."
        python3 -m venv "$ROOT_DIR/.venv"
    fi

    # Activate venv
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.venv/bin/activate"

    # Install dependencies if needed
    if [[ ! -f "$ROOT_DIR/.venv/.installed" ]]; then
        log_info "Installing dependencies..."
        pip install -q -r requirements.txt
        touch "$ROOT_DIR/.venv/.installed"
    fi

    # Ensure data directory exists
    mkdir -p "$ROOT_DIR/data"
    mkdir -p "$ROOT_DIR/repositories"

    # Start the application
    if [[ "$DEV_MODE" == "true" ]]; then
        log_info "Starting in development mode..."
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    else
        log_info "Starting GitPulse server..."
        uvicorn app.main:app --host 0.0.0.0 --port 8000
    fi
fi
