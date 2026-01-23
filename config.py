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

# Ollama settings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "codellama:7b")
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
