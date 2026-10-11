# GitPulse

AI-powered Git repository contributor analysis tool. Analyzes multiple repositories to determine the impact and code quality of individual contributors.

## Features

- **Multi-Repository Analysis**: Analyze all repositories in the `./repositories` directory
- **Contributor Metrics**: Track commits, lines changed, and contribution frequency
- **Code Quality Analysis**: AI-powered code quality assessment using Ollama
- **Branch Coverage**: Analyzes all branches and commits
- **PR Detection**: Identifies and counts pull request contributions
- **Top Contributors**: Ranked leaderboards per repository
- **Web Dashboard**: Interactive web interface for exploring results

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitPulse                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │  Web UI     │   │  REST API   │   │  Analysis Engine    │   │
│  │  Dashboard  │◄──│  FastAPI    │◄──│  - Git Analysis     │   │
│  │             │   │             │   │  - Quality Scoring  │   │
│  └─────────────┘   └─────────────┘   │  - Contributor Rank │   │
│                                       └──────────┬──────────┘   │
│                                                  │              │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────▼──────────┐   │
│  │ Repositories│   │  Database   │   │  Ollama (host)      │   │
│  │ ./repos/*   │   │  SQLite     │   │  Code Quality LLM   │   │
│  └─────────────┘   └─────────────┘   └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+
- Git

### Installation

```bash
# Clone the repository
git clone <repo-url> git-pulse
cd git-pulse

# Start the app in Docker (checks the Ollama model first)
./start --docker

# Stop services
./scripts/stop.sh --docker

# Or run locally for development (no Docker)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

### Add Repositories to Analyze

Clone or copy repositories into the `./repositories` directory:

```bash
cd repositories
git clone https://github.com/user/repo1.git
git clone https://github.com/user/repo2.git
```

### Access the Dashboard

Open http://localhost:8000 in your browser.

## Using the App (Scripts)

```bash
# Start with Docker (the app; Ollama is the machine's own)
./scripts/start.sh --docker

# Rebuild containers and start
./scripts/start.sh --docker -b

# Stop Docker services
./scripts/stop.sh --docker

# Start locally with auto-reload
./scripts/start.sh --dev
```

## Docs

See `docs/README.md` for a detailed feature overview and usage guide.

## Configuration

Edit `config.py` or set environment variables:

```bash
# Ollama settings
OLLAMA_RUNTIME=host                    # or container (see "Ollama" below)
OLLAMA_HOST=http://localhost:11434     # local app
OLLAMA_MODEL=                          # empty: ai-models.env decides

# Analysis settings
ANALYSIS_DEPTH=full          # full | recent | shallow
MAX_COMMITS_PER_REPO=10000
QUALITY_SAMPLE_SIZE=50       # Commits to sample for quality analysis

# Database
DATABASE_URL=sqlite:///data/gitpulse.db
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/repositories` | GET | List all repositories |
| `/api/repositories/{name}` | GET | Get repository details |
| `/api/repositories/{name}/analyze` | POST | Trigger analysis |
| `/api/contributors` | GET | List all contributors |
| `/api/contributors/{email}` | GET | Get contributor details |
| `/api/leaderboard` | GET | Global contributor rankings |
| `/api/leaderboard/{repo}` | GET | Per-repository rankings |
| `/api/status` | GET | Analysis status |

## Metrics Calculated

### Per Contributor
- Total commits
- Lines added / removed
- Files touched
- Commit frequency (commits per day/week)
- Active branches
- PR count (detected from merge commits)
- Code quality score (AI-analyzed)

### Code Quality Factors
- Code complexity
- Documentation presence
- Test coverage indicators
- Consistency with project style
- Commit message quality

## Tech Stack

- **Backend**: Python, FastAPI
- **Database**: SQLite
- **AI/LLM**: Ollama, the code model in `ai-models.env`
- **Git Analysis**: GitPython
- **Frontend**: Vanilla JS, Chart.js
- **Container**: Docker, Docker Compose

## Development

```bash
# Run in development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

```

## Ollama

GitPulse uses the machine's own Ollama by default: `http://localhost:11434`
for a local app, `http://host.docker.internal:11434` from the app container
(`OLLAMA_BASE_URL_DOCKER`). The model is `OLLAMA_MODEL` in `ai-models.env`,
generated from the fleet model registry (the code model, `qwen2.5-coder:7b`);
do not edit it, set `OLLAMA_MODEL` in `.env` to use another model on one
machine.

`./start` (or `./scripts/start.sh`) checks that the Ollama has the model first
and offers to pull a missing one; with no terminal it stops and names the pull.
It needs the script-helpers submodule: `git submodule update --init`.
`GITPULSE_SKIP_OLLAMA=1` skips the check.

No Ollama on the machine? Optional, only if needed: `OLLAMA_RUNTIME=container`
in `.env` makes `./start --docker` add `docker-ollama.yml`, a compose override
with an `ollama` container on `127.0.0.1:${OLLAMA_CONTAINER_PORT:-11435}`,
check the model in it, and point the app at it. `./scripts/stop.sh --docker`
always includes that file, so the container is stopped too. Its models live in the external volume
`git-pulse_ollama_data`, which `docker compose down -v` does not remove.

## License

MIT

---

## Clone traffic

![Clone traffic](https://raw.githubusercontent.com/nikolareljin/stats/main/charts/git-pulse.svg)

_Updated daily. Total and unique cloners over the last 14 days._
