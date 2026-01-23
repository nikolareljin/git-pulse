# GitPulse Docs

## Overview
GitPulse is a self-hosted dashboard for analyzing multiple Git repositories. It combines commit analytics, heuristic PR analysis, and static codebase signals to surface repository health and contributor impact.

## Features

### Repository Analysis
- Multi-repo scanning from `./repositories`
- Commit activity and branch coverage
- Repo scores (activity, health, quality, diversity)
- Static codebase analysis (complexity, comments, tests, dependency risk)

### Contributor Analysis
- Commits, lines changed, PR counts
- Impact and quality scores
- PR quality scoring based on inferred PRs (merge commits only)
- Merge/unmerge contributors with multiple identities

### Web Dashboard
- Portfolio summary and score breakdown
- Repository cards and score comparisons
- Contributor leaderboard with PR quality
- Live status and analysis history

## How It Works

### Heuristic PR Detection
PRs are inferred from merge commits that match common patterns such as:
- "merge pull request"
- "merged pr"
- "pull request #"

For each inferred PR, GitPulse gathers commits between the merge parents and attributes those commits to their authors. PR quality scores are derived from aggregated diff content (not from the merge commit author only).

### Static Codebase Analysis
Each repository is scanned for supported file types (PHP, JavaScript/TypeScript, Python, Groovy/Gradle, Dockerfiles, Bash). The analyzer computes:
- Complexity (keyword-based cyclomatic approximation)
- Comment density
- Test presence (by file paths/patterns)
- Dependency hygiene (lockfiles and version pinning checks)

## Usage

### 1) Add Repositories
Place repositories inside `./repositories`:

```bash
cd repositories
git clone https://github.com/user/repo1.git
git clone https://github.com/user/repo2.git
```

### 2) Start the App

```bash
# Docker (recommended)
./scripts/start.sh --docker

# Rebuild containers
./scripts/start.sh --docker -b

# Stop services
./scripts/stop.sh --docker
```

### 3) Run Analysis
Use the dashboard buttons:
- "Discover Repositories" to register repos
- "Analyze" on each repo, or "Analyze All Repositories"

### 4) View Results
- Portfolio score shows overall health and quality
- Repository scores highlight repo-level trends
- Leaderboard shows contributor impact and PR quality

### 5) Merge Contributors
In the leaderboard:
- Select multiple rows
- Click "Merge Selected" (first selected is the primary)
- To undo, select any in the group and click "Unmerge Selected"

## API Highlights

- `GET /api/repositories` list repositories
- `POST /api/repositories/{name}/analyze` analyze a repo
- `GET /api/scores/summary` quick portfolio summary
- `GET /api/leaderboard` global contributor rankings
- `GET /api/repositories/{name}/codebase` static codebase report

## Notes and Limitations
- PR detection is heuristic; squash/rebase merges may be missed.
- Static analysis is best-effort; it does not run language-specific linters.
- For accurate PR metadata, external integrations would be required.
