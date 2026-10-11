# Repository Guidelines

## Project Structure & Module Organization

```
git-pulse/
├── app/                    # Main application code
│   ├── main.py            # FastAPI application entry point
│   ├── api/               # REST API routes
│   │   └── routes.py      # API endpoints
│   ├── analyzer/          # Analysis engine
│   │   ├── git_analyzer.py    # Git repository parsing
│   │   ├── contributor.py     # Contributor metrics
│   │   ├── quality.py         # Code quality analysis
│   │   └── ollama.py          # Ollama LLM client
│   ├── models/            # Database models
│   │   └── database.py    # SQLAlchemy models
│   └── templates/         # Jinja2 HTML templates
├── static/                # Static web assets
│   ├── css/              # Stylesheets
│   └── js/               # JavaScript
├── repositories/          # Git repos to analyze (not committed)
├── data/                  # SQLite database (not committed)
├── docker-compose.yml     # Docker services (App; Ollama fallback in profile "ollama")
├── Dockerfile            # App container
├── requirements.txt      # Python dependencies
└── config.py             # Configuration settings
```

## Build, Test, and Development Commands

### Local Development
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use Python directly
python -m app.main
```

### Docker Deployment
```bash
# Start the app (checks the Ollama model in ai-models.env first)
./start --docker

# View logs
docker-compose logs -f gitpulse

# Stop services
docker-compose down
```

### Ollama Setup
```bash
# The machine's own Ollama; ./start checks OLLAMA_MODEL (ai-models.env)
# and offers to pull it. OLLAMA_RUNTIME=container uses the fallback container.
curl http://localhost:11434/api/tags
```

## Coding Style & Naming Conventions

- Python code follows PEP 8: 4-space indentation, snake_case for variables/functions, PascalCase for classes
- Async functions use `async def` and are named with verb prefixes (e.g., `fetch_`, `load_`, `analyze_`)
- API endpoints follow REST conventions: GET for reads, POST for actions
- Database models use singular nouns (e.g., `Repository`, `Contributor`)
- JavaScript follows camelCase for variables/functions
- CSS uses kebab-case for class names with BEM-like patterns

## Testing Guidelines

- No automated test suite yet
- Test locally with sample repositories in `./repositories/`
- API endpoints can be tested via `/docs` (Swagger UI)
- Check Ollama connectivity at `/api/status/ollama`

## Configuration & Security

- Environment variables override `config.py` defaults
- Never commit `data/` directory (contains database)
- Never commit `repositories/` directory (contains analyzed repos)
- Ollama runs locally - no external API calls for code analysis
- Database is SQLite by default, path configurable via `DATABASE_URL`

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/repositories` | GET | List repositories |
| `/api/repositories/discover` | GET | Scan for new repos |
| `/api/repositories/{name}/analyze` | POST | Start analysis |
| `/api/analyze/all` | POST | Analyze all repos |
| `/api/contributors` | GET | List contributors |
| `/api/leaderboard` | GET | Global rankings |
| `/api/leaderboard/{repo}` | GET | Per-repo rankings |
| `/api/status` | GET | Analysis status |
| `/api/status/ollama` | GET | Ollama health |
| `/api/stats` | GET | Global statistics |
