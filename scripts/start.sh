#!/usr/bin/env bash
set -euo pipefail

# GitPulse - Start Script
# Starts the GitPulse application, after checking its Ollama has the model

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load script helpers
SCRIPT_HELPERS_DIR="${SCRIPT_HELPERS_DIR:-$ROOT_DIR/vendor/script-helpers}"
if [[ -f "$SCRIPT_HELPERS_DIR/helpers.sh" ]]; then
    # shellcheck disable=SC1091
    source "$SCRIPT_HELPERS_DIR/helpers.sh"
    shlib_import logging ollama_endpoint
else
    echo "[ERROR] Missing script-helpers. Run: git submodule update --init vendor/script-helpers" >&2
    exit 1
fi

cd "$ROOT_DIR"
# shellcheck source=scripts/ollama.sh
source "$SCRIPT_DIR/ollama.sh"

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
            echo ""
            echo "The model is OLLAMA_MODEL in ai-models.env; it is checked first and a"
            echo "missing one is pulled after a yes. GITPULSE_SKIP_OLLAMA=1 skips the check."
            echo "OLLAMA_RUNTIME=container in .env uses the ollama container instead of the"
            echo "machine's Ollama."
            exit 0
            ;;
        *)
            echo "Unknown option: $arg (see --help)" >&2
            exit 1
            ;;
    esac
done

mode=local
[[ "$USE_DOCKER" != "true" ]] || mode=docker
gp_ollama_runtime "$ROOT_DIR" "$mode" || exit
gp_ensure_ollama_models "$ROOT_DIR" "$mode" || exit

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

    log_info "GitPulse is running!"
    echo ""
    echo "  Dashboard: http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/docs"
    echo "  Ollama:    ${GP_OLLAMA_URL} (${GP_OLLAMA_RUNTIME})"
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
