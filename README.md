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
│  │ Repositories│   │  Database   │   │  Ollama (Docker)    │   │
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

# Start services (Ollama + App)
docker-compose up -d

# Or run locally for development
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

## Configuration

Edit `config.py` or set environment variables:

```bash
# Ollama settings
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=codellama:7b

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
- **AI/LLM**: Ollama with CodeLlama
- **Git Analysis**: GitPython
- **Frontend**: Vanilla JS, Chart.js
- **Container**: Docker, Docker Compose

## Development

```bash
# Run in development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Ollama separately
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker exec -it ollama ollama pull codellama:7b
```

## License

MIT
