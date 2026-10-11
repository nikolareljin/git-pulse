"""scripts/ollama.sh and config.py: which Ollama and which model GitPulse uses.

The script-helpers functions are stubs here; docker and curl are stubs on PATH.
"""
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run(tmp_path, mode="docker", env_file="", ensure_rc=0, reach_rc=0, **env_extra):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    log = tmp_path / "docker-args"
    (bindir / "docker").write_text(f'#!/bin/sh\necho "$*" >> {log}\nexit 0\n')
    (bindir / "curl").write_text("#!/bin/sh\nexit 0\n")
    for f in bindir.iterdir():
        f.chmod(0o755)
    (tmp_path / ".env").write_text(env_file)
    (tmp_path / "ai-models.env").write_text("OLLAMA_MODEL=coder:7b\n")
    script = f"""
log_info() {{ :; }}; log_warn() {{ echo "warn: $*"; }}; log_error() {{ echo "error: $*"; }}
ollama_models_file_get() {{ sed -n "s/^$2=//p" "$1" | tail -n 1; }}
ollama_project_ensure_models() {{ echo "ensure:${{!OLLAMA_URL_VARS}}:${{OLLAMA_MODE:-}}:${{OLLAMA_HOST_PORT:-}}:$AI_MODEL_TIER:$OLLAMA_PULL_MISSING"; return {ensure_rc}; }}
ollama_endpoint_container_reach() {{ echo "reach:$1"; return {reach_rc}; }}
source "{ROOT}/scripts/ollama.sh"
rc=0; gp_ollama_runtime "{tmp_path}" {mode} || rc=$?
echo "runtime rc=$rc profiles=${{COMPOSE_PROFILES:-}} docker=${{OLLAMA_BASE_URL_DOCKER:-}} host=${{OLLAMA_HOST:-}}"
[ "$rc" -ne 0 ] || {{ gp_ensure_ollama_models "{tmp_path}" {mode}; echo "ensure rc=$?"; }}
"""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OLLAMA_", "GITPULSE_", "GP_", "AI_", "COMPOSE_"))}
    env["PATH"] = f"{bindir}:{env['PATH']}"
    env.update(env_extra)
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env, timeout=30)
    return r.stdout + r.stderr, (log.read_text() if log.exists() else "")


def test_docker_uses_the_host_ollama_by_default(tmp_path):
    out, docker = _run(tmp_path)
    assert "runtime rc=0 profiles= docker=http://host.docker.internal:11434" in out, out
    assert "ensure:http://host.docker.internal:11434:::standard:ask" in out
    assert "reach:http://host.docker.internal:11434" in out and "ensure rc=0" in out
    assert docker == ""


def test_local_uses_localhost_and_needs_no_container_reach(tmp_path):
    out, _ = _run(tmp_path, mode="local")
    assert "host=http://localhost:11434" in out and "ensure:http://localhost:11434:" in out, out
    assert "reach:" not in out and "ensure rc=0" in out


def test_a_docker_url_to_the_container_needs_the_container_runtime(tmp_path):
    out, docker = _run(tmp_path, env_file="OLLAMA_BASE_URL_DOCKER=http://ollama:11434\n")
    assert "runtime rc=9" in out and "OLLAMA_RUNTIME=container" in out, out
    assert docker == ""


def test_container_runtime_starts_it_and_checks_the_model_in_it(tmp_path):
    out, docker = _run(tmp_path, env_file="OLLAMA_RUNTIME=container\nOLLAMA_CONTAINER_PORT=11500\n")
    assert "runtime rc=0 profiles=ollama docker=http://ollama:11434" in out, out
    assert "ensure:http://ollama:11434:docker:11500:standard:ask" in out
    assert "reach:" not in out
    assert "volume inspect git-pulse_ollama_data" in docker and "compose up -d ollama" in docker


def test_container_runtime_gives_a_local_app_the_published_port(tmp_path):
    out, _ = _run(tmp_path, mode="local", env_file="OLLAMA_RUNTIME=container\n")
    assert "host=http://127.0.0.1:11435" in out, out


@pytest.mark.parametrize("value", ["cloud", "Host"])
def test_an_unknown_runtime_is_refused(tmp_path, value):
    out, docker = _run(tmp_path, env_file=f"OLLAMA_RUNTIME={value}\n")
    assert "runtime rc=9" in out and "use host" in out, out
    assert docker == ""


@pytest.mark.parametrize("port", ["0", "70000", "abc"])
def test_a_bad_container_port_is_refused(tmp_path, port):
    out, docker = _run(tmp_path, env_file=f"OLLAMA_RUNTIME=container\nOLLAMA_CONTAINER_PORT={port}\n")
    assert "runtime rc=9" in out and "not a port" in out, out
    assert docker == ""


def test_no_ollama_answering_stops_and_names_the_fallback(tmp_path):
    out, _ = _run(tmp_path, ensure_rc=4)
    assert "ensure rc=4" in out and "OLLAMA_RUNTIME=container" in out, out


def test_a_missing_model_stops_the_start(tmp_path):
    out, _ = _run(tmp_path, ensure_rc=5)
    assert "ensure rc=5" in out, out


def test_an_unreachable_host_ollama_stops_the_start(tmp_path):
    out, _ = _run(tmp_path, reach_rc=1)
    assert "ensure rc=1" in out, out


def test_a_model_in_env_is_named(tmp_path):
    out, _ = _run(tmp_path, env_file="OLLAMA_MODEL=codellama:7b\n")
    assert "OLLAMA_MODEL=codellama:7b in .env or the environment wins over coder:7b" in out, out


def test_skip_skips_the_check(tmp_path):
    out, _ = _run(tmp_path, GITPULSE_SKIP_OLLAMA="1")
    assert "ensure rc=0" in out and "ensure:" not in out, out


def test_the_models_volume_survives_down_v():
    block = (ROOT / "docker-compose.yml").read_text().split("\n  ollama_data:\n", 1)[1]
    assert "external: true" in block and "name: git-pulse_ollama_data" in block


def test_the_model_comes_from_ai_models_env(monkeypatch):
    import importlib

    import config
    monkeypatch.setenv("OLLAMA_MODEL", "")
    importlib.reload(config)
    assert config.OLLAMA_MODEL == config.ai_models()["OLLAMA_MODEL"] != ""
    monkeypatch.setenv("OLLAMA_MODEL", "other:1b")
    importlib.reload(config)
    assert config.OLLAMA_MODEL == "other:1b"


def test_ai_models_file_parsing(tmp_path):
    import config
    f = tmp_path / "ai-models.env"
    f.write_text('﻿# c\nexport OLLAMA_MODEL = "a:1b"  # x\nOTHER=b\n\nbad line\n', encoding="utf-8")
    assert config.ai_models(f) == {"OLLAMA_MODEL": "a:1b", "OTHER": "b"}
    assert config.ai_models(tmp_path / "missing") == {}
