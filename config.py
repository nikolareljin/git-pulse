"""GitPulse Configuration"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
REPOSITORIES_DIR = BASE_DIR / "repositories"
DATA_DIR = BASE_DIR / "data"

# Ensure directories exist
REPOSITORIES_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/gitpulse.db")



def ai_models(path: Path = BASE_DIR / "ai-models.env") -> dict:
    """NAME=model lines of ai-models.env (generated from the fleet model registry)."""
    models = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.split(" #", 1)[0].strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.removeprefix("export ").split("=", 1)
            models[name.strip()] = value.strip().strip("'\"")
    return models


# Ollama settings. The model: OLLAMA_MODEL in the environment (from .env via
# compose), else ai-models.env. An empty value counts as unset.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") or ai_models().get("OLLAMA_MODEL", "")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# Analysis settings
ANALYSIS_DEPTH = os.getenv("ANALYSIS_DEPTH", "full")  # full | recent | shallow
MAX_COMMITS_PER_REPO = int(os.getenv("MAX_COMMITS_PER_REPO", "10000"))
QUALITY_SAMPLE_SIZE = int(os.getenv("QUALITY_SAMPLE_SIZE", "50"))
MAX_DIFF_SIZE = int(os.getenv("MAX_DIFF_SIZE", "10000"))  # Max characters per diff

# Web server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Quality analysis weights
QUALITY_WEIGHTS = {
    "commit_message": 0.15,
    "code_complexity": 0.25,
    "documentation": 0.15,
    "test_coverage": 0.20,
    "consistency": 0.15,
    "best_practices": 0.10,
}
