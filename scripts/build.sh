#!/usr/bin/env bash
set -euo pipefail

# GitPulse - Build Script
# Builds Docker images and prepares the application

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
BUILD_DOCKER=false
INSTALL_DEPS=false
PULL_MODEL=false

for arg in "$@"; do
    case $arg in
        --docker)
            BUILD_DOCKER=true
            ;;
        --deps)
            INSTALL_DEPS=true
            ;;
        --model)
            PULL_MODEL=true
            ;;
        --all)
            BUILD_DOCKER=true
            INSTALL_DEPS=true
            PULL_MODEL=true
            ;;
        --help|-h)
            echo "Usage: $0 [--docker] [--deps] [--model] [--all]"
            echo ""
            echo "Options:"
            echo "  --docker    Build Docker images"
            echo "  --deps      Install Python dependencies"
            echo "  --model     Pull Ollama model"
            echo "  --all       Do all of the above"
            exit 0
            ;;
    esac
done

# Default to --deps if no args
if [[ "$BUILD_DOCKER" == "false" && "$INSTALL_DEPS" == "false" && "$PULL_MODEL" == "false" ]]; then
    INSTALL_DEPS=true
fi

# Initialize git submodules
if [[ -f "$ROOT_DIR/.gitmodules" ]]; then
    log_info "Initializing git submodules..."
    git submodule update --init --recursive
fi

# Install Python dependencies
if [[ "$INSTALL_DEPS" == "true" ]]; then
    log_info "Setting up Python environment..."

    if [[ ! -d "$ROOT_DIR/.venv" ]]; then
        python3 -m venv "$ROOT_DIR/.venv"
    fi

    # shellcheck disable=SC1091
    source "$ROOT_DIR/.venv/bin/activate"

    log_info "Installing dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt

    touch "$ROOT_DIR/.venv/.installed"
    log_info "Python dependencies installed"
fi

# Build Docker images
if [[ "$BUILD_DOCKER" == "true" ]]; then
    log_info "Building Docker images..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker not found"
        exit 1
    fi

    docker compose build

    log_info "Docker images built"
fi

# Pull Ollama model
if [[ "$PULL_MODEL" == "true" ]]; then
    log_info "Pulling Ollama model..."

    if docker ps | grep -q gitpulse-ollama; then
        docker exec gitpulse-ollama ollama pull codellama:7b
    else
        log_warn "Ollama container not running. Start with: ./scripts/start.sh --docker"
        log_info "Then run: docker exec -it gitpulse-ollama ollama pull codellama:7b"
    fi
fi

# Create necessary directories
mkdir -p "$ROOT_DIR/data"
mkdir -p "$ROOT_DIR/repositories"

log_info "Build complete!"
echo ""
echo "Next steps:"
echo "  1. Add repositories to ./repositories/"
echo "  2. Start the app: ./scripts/start.sh"
echo "  3. Open dashboard: http://localhost:8000"
