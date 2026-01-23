#!/usr/bin/env bash
set -euo pipefail

# GitPulse - Analyze Script
# Triggers analysis of repositories via the API

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

# Configuration
API_HOST="${GITPULSE_HOST:-http://localhost:8000}"

# Parse arguments
REPO_NAME=""
ANALYZE_ALL=false
NO_LLM=false

for arg in "$@"; do
    case $arg in
        --all)
            ANALYZE_ALL=true
            ;;
        --no-llm)
            NO_LLM=true
            ;;
        --help|-h)
            echo "Usage: $0 [repo-name] [--all] [--no-llm]"
            echo ""
            echo "Arguments:"
            echo "  repo-name    Name of repository to analyze"
            echo ""
            echo "Options:"
            echo "  --all        Analyze all repositories"
            echo "  --no-llm     Skip LLM-based quality analysis"
            exit 0
            ;;
        -*)
            # Skip other flags
            ;;
        *)
            REPO_NAME="$arg"
            ;;
    esac
done

# Check if API is available
log_info "Checking GitPulse API..."
if ! curl -s "$API_HOST/health" > /dev/null 2>&1; then
    log_error "GitPulse API not available at $API_HOST"
    log_error "Start the server first: ./scripts/start.sh"
    exit 1
fi

# Build query params
QUERY_PARAMS=""
if [[ "$NO_LLM" == "true" ]]; then
    QUERY_PARAMS="?use_llm=false"
fi

# Trigger analysis
if [[ "$ANALYZE_ALL" == "true" ]]; then
    log_info "Triggering analysis for all repositories..."
    RESPONSE=$(curl -s -X POST "$API_HOST/api/analyze/all$QUERY_PARAMS")
elif [[ -n "$REPO_NAME" ]]; then
    log_info "Triggering analysis for: $REPO_NAME"
    RESPONSE=$(curl -s -X POST "$API_HOST/api/repositories/$REPO_NAME/analyze$QUERY_PARAMS")
else
    log_error "Specify a repository name or use --all"
    echo ""
    echo "Available repositories:"
    curl -s "$API_HOST/api/repositories/discover" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for repo in data.get('discovered', []):
    print(f\"  - {repo['name']}\")
" 2>/dev/null || echo "  (could not fetch list)"
    exit 1
fi

echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Message: {data.get('message', 'Unknown')}\")
if 'run_id' in data:
    print(f\"Run ID: {data['run_id']}\")
" 2>/dev/null || echo "$RESPONSE"

log_info "Analysis started. Check status at: $API_HOST"
