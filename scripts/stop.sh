#!/usr/bin/env bash
set -euo pipefail

# GitPulse - Stop Script
# Stops the GitPulse application and related services

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

for arg in "$@"; do
    case $arg in
        --docker)
            USE_DOCKER=true
            ;;
        --help|-h)
            echo "Usage: $0 [--docker]"
            echo ""
            echo "Options:"
            echo "  --docker    Stop Docker Compose services"
            exit 0
            ;;
    esac
done

if [[ "$USE_DOCKER" == "true" ]]; then
    log_info "Stopping Docker Compose services..."
    docker compose down
    log_info "Services stopped"
else
    log_info "Stopping local GitPulse processes..."

    # Find and kill uvicorn processes
    pkill -f "uvicorn app.main:app" 2>/dev/null || true

    log_info "GitPulse stopped"
fi
