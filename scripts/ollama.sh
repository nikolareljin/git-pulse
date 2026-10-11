#!/usr/bin/env bash
# Which Ollama GitPulse uses, and the model check before it starts.
# Sourced by scripts/start.sh after script-helpers (logging, ollama_endpoint).
#
# OLLAMA_RUNTIME=host (default): the machine's one Ollama. The app container
# reaches it at OLLAMA_BASE_URL_DOCKER (default host.docker.internal:11434), a
# local app at OLLAMA_HOST (default localhost:11434).
# OLLAMA_RUNTIME=container: the optional container in docker-ollama.yml (a
# compose override) on 127.0.0.1:OLLAMA_CONTAINER_PORT (default 11435), models
# in the external volume git-pulse_ollama_data.

GP_OLLAMA_VOLUME="git-pulse_ollama_data"

# A value from the environment, else from .env (empty if neither).
_gp_setting() {
  local name="$1" root="$2" value
  value="${!name:-}"
  [[ -n "$value" ]] || value="$(ollama_models_file_get "$root/.env" "$name" 2>/dev/null)" || value=""
  printf '%s' "$value"
}

_gp_names_the_container() {
  case "$1" in
    ollama|ollama:*|http://ollama|http://ollama[:/]*|https://ollama|https://ollama[:/]*) return 0 ;;
  esac
  return 1
}

# Decides the Ollama and exports what compose and the app read:
# COMPOSE_FILE, OLLAMA_BASE_URL_DOCKER (docker) or OLLAMA_HOST (local),
# and GP_OLLAMA_URL, the address the model check asks.
#   gp_ollama_runtime <root> docker|local
gp_ollama_runtime() {
  local root="${1:?gp_ollama_runtime needs the repository root}" mode="${2:?docker or local}" url port
  GP_OLLAMA_RUNTIME="$(_gp_setting OLLAMA_RUNTIME "$root")"
  GP_OLLAMA_RUNTIME="${GP_OLLAMA_RUNTIME:-host}"
  export GP_OLLAMA_RUNTIME
  case "$GP_OLLAMA_RUNTIME" in
    host)
      if [[ "$mode" == "docker" ]]; then
        url="$(_gp_setting OLLAMA_BASE_URL_DOCKER "$root")"
        url="${url:-http://host.docker.internal:11434}"
        if _gp_names_the_container "$url"; then
          log_error "OLLAMA_BASE_URL_DOCKER=$url names the ollama container, which runs only with OLLAMA_RUNTIME=container."
          log_error "Set OLLAMA_RUNTIME=container in .env for it, or OLLAMA_BASE_URL_DOCKER=http://host.docker.internal:11434, or delete the line."
          return 9
        fi
        export OLLAMA_BASE_URL_DOCKER="$url"
      else
        url="${OLLAMA_HOST:-http://localhost:11434}"
        export OLLAMA_HOST="$url"
        # The local app does not read .env; give it the model the check uses.
        local model
        model="$(_gp_setting OLLAMA_MODEL "$root")"
        [[ -z "$model" ]] || export OLLAMA_MODEL="$model"
      fi
      export GP_OLLAMA_URL="$url"
      export COMPOSE_FILE=docker-compose.yml
      ;;
    container)
      port="$(_gp_setting OLLAMA_CONTAINER_PORT "$root")"
      port="${port:-11435}"
      if ! [[ "$port" =~ ^[0-9]+$ ]] || (( 10#$port < 1 || 10#$port > 65535 )); then
        log_error "OLLAMA_CONTAINER_PORT=$port is not a port (1-65535)."
        return 9
      fi
      export OLLAMA_CONTAINER_PORT="$((10#$port))"
      export COMPOSE_FILE=docker-compose.yml:docker-ollama.yml
      export OLLAMA_BASE_URL_DOCKER=http://ollama:11434
      [[ "$mode" == "docker" ]] || export OLLAMA_HOST="http://127.0.0.1:${OLLAMA_CONTAINER_PORT}"
      export GP_OLLAMA_URL=http://ollama:11434
      ;;
    *)
      log_error "OLLAMA_RUNTIME=$GP_OLLAMA_RUNTIME: use host (the machine's Ollama) or container (the optional container in docker-ollama.yml)."
      return 9
      ;;
  esac
}

# The container fallback: its volume (external, so `docker compose down -v`
# keeps the models) and the service, before the model check asks it.
gp_start_ollama_container() {
  local _
  docker volume inspect "$GP_OLLAMA_VOLUME" >/dev/null 2>&1 \
    || docker volume create "$GP_OLLAMA_VOLUME" >/dev/null \
    || { log_error "Could not create the Docker volume $GP_OLLAMA_VOLUME."; return 1; }
  docker compose up -d ollama || { log_error "The ollama container did not start."; return 1; }
  for _ in $(seq 1 30); do
    curl -fsS -m 2 "http://127.0.0.1:${OLLAMA_CONTAINER_PORT}/api/version" >/dev/null 2>&1 && return 0
    sleep 1
  done
  log_error "The ollama container does not answer on 127.0.0.1:${OLLAMA_CONTAINER_PORT}."
  return 4
}

# Checks the model ai-models.env names (OLLAMA_MODEL) on that Ollama; a
# missing one is pulled after a yes. GITPULSE_SKIP_OLLAMA=1 skips it.
#   gp_ensure_ollama_models <root> docker|local
gp_ensure_ollama_models() {
  local root="${1:?gp_ensure_ollama_models needs the repository root}" mode="${2:?docker or local}"
  local chosen default tier rc=0
  if [[ "${GITPULSE_SKIP_OLLAMA:-}" == "1" ]]; then
    log_warn "GITPULSE_SKIP_OLLAMA=1: the Ollama model check is skipped."
    return 0
  fi
  chosen="$(_gp_setting OLLAMA_MODEL "$root")"
  default="$(ollama_models_file_get "$root/ai-models.env" OLLAMA_MODEL 2>/dev/null)" || default=""
  if [[ -n "$chosen" && "$chosen" != "$default" ]]; then
    log_warn "OLLAMA_MODEL=$chosen in .env or the environment wins over $default from ai-models.env. Remove it there to use ai-models.env."
  fi
  # The app reads OLLAMA_MODEL only, not the per-machine-class columns, so the
  # check must look for that same model.
  tier="$(_gp_setting AI_MODEL_TIER "$root")"
  if [[ -n "$tier" && "$tier" != "standard" ]]; then
    log_warn "AI_MODEL_TIER=$tier is not used: the app reads OLLAMA_MODEL only."
  fi
  export AI_MODEL_TIER=standard
  if [[ -z "$(_gp_setting OLLAMA_PULL_MISSING "$root")" ]]; then
    export OLLAMA_PULL_MISSING=ask
  fi
  export OLLAMA_URL_VARS=GP_OLLAMA_URL

  if [[ "$GP_OLLAMA_RUNTIME" == "container" ]]; then
    gp_start_ollama_container || return
    export OLLAMA_MODE=docker OLLAMA_HOST_PORT="$OLLAMA_CONTAINER_PORT"
    ollama_project_ensure_models "$root/ai-models.env" "$root/.env" OLLAMA_MODEL
    return
  fi

  ollama_project_ensure_models "$root/ai-models.env" "$root/.env" OLLAMA_MODEL || rc=$?
  if [[ "$rc" -eq 4 ]]; then
    log_error "No Ollama on this machine answers. Install one, or use the container fallback: OLLAMA_RUNTIME=container in .env."
  fi
  [[ "$rc" -eq 0 ]] || return "$rc"
  # Answering on 127.0.0.1 does not prove the app container can reach it.
  [[ "$mode" != "docker" ]] || ollama_endpoint_container_reach "$GP_OLLAMA_URL"
}
