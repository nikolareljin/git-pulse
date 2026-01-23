#!/usr/bin/env bash
set -euo pipefail

# GitPulse - Update Script
# Updates git submodules and dependencies

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
UPDATE_SUBMODULES=true
UPDATE_DEPS=false
UPDATE_DOCKER=false

for arg in "$@"; do
    case $arg in
        --deps)
            UPDATE_DEPS=true
            ;;
        --docker)
            UPDATE_DOCKER=true
            ;;
        --all)
            UPDATE_DEPS=true
            UPDATE_DOCKER=true
            ;;
        --no-submodules)
            UPDATE_SUBMODULES=false
            ;;
        --help|-h)
            echo "Usage: $0 [--deps] [--docker] [--all] [--no-submodules]"
            echo ""
            echo "Options:"
            echo "  --deps          Update Python dependencies"
            echo "  --docker        Update Docker images"
            echo "  --all           Update everything"
            echo "  --no-submodules Skip git submodule update"
            exit 0
            ;;
    esac
done

# Update git submodules
if [[ "$UPDATE_SUBMODULES" == "true" ]]; then
    log_info "Updating git submodules..."

    git submodule update --init --recursive
    git submodule update --remote --merge

    log_info "Submodules updated"
fi

# Update Python dependencies
if [[ "$UPDATE_DEPS" == "true" ]]; then
    log_info "Updating Python dependencies..."

    if [[ ! -d "$ROOT_DIR/.venv" ]]; then
        python3 -m venv "$ROOT_DIR/.venv"
    fi

    # shellcheck disable=SC1091
    source "$ROOT_DIR/.venv/bin/activate"

    pip install -q --upgrade pip
    pip install -q --upgrade -r requirements.txt

    touch "$ROOT_DIR/.venv/.installed"
    log_info "Python dependencies updated"
fi

# Update Docker images
if [[ "$UPDATE_DOCKER" == "true" ]]; then
    log_info "Updating Docker images..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker not found"
        exit 1
    fi

    docker compose pull
    docker compose build --pull

    log_info "Docker images updated"
fi

log_info "Update complete!"
