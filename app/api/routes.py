"""API Routes for GitPulse"""

import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    Repository, Contributor, Commit, ContributorStats, AnalysisRun,
    get_session
)
from app.analyzer import GitAnalyzer, ContributorAnalyzer, QualityAnalyzer, OllamaClient
from app.analyzer.git_analyzer import discover_repositories

import config

logger = logging.getLogger(__name__)
router = APIRouter()


# ============== Pydantic Models ==============

class RepositoryResponse(BaseModel):
    id: int
    name: str
    path: str
    url: Optional[str]
    default_branch: str
    total_commits: int
    total_contributors: int
    total_branches: int
    last_analyzed: Optional[datetime]

    class Config:
        from_attributes = True


class ContributorResponse(BaseModel):
    id: int
    email: str
    name: str
    total_commits: int
    total_lines_added: int
    total_lines_removed: int
    total_prs: int
    quality_score: float
    impact_score: float
    first_commit: Optional[datetime]
    last_commit: Optional[datetime]

    class Config:
        from_attributes = True


class ContributorStatsResponse(BaseModel):
    contributor_email: str
    contributor_name: str
    repository_name: str
    commits: int
    lines_added: int
    lines_removed: int
    prs: int
    quality_score: float
    impact_score: float
    rank: Optional[int]

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    rank: int
    email: str
    name: str
    commits: int
    lines_changed: int
    prs: int
    quality_score: float
    impact_score: float


class AnalysisStatus(BaseModel):
    repository: str
    status: str
    commits_analyzed: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]


class OllamaStatus(BaseModel):
    available: bool
    host: str
    model: str


# ============== Repository Endpoints ==============

@router.get("/repositories", response_model=List[RepositoryResponse])
async def list_repositories(session: AsyncSession = Depends(get_session)):
    """List all repositories"""
    result = await session.execute(select(Repository).order_by(Repository.name))
    repos = result.scalars().all()
    return repos


@router.post("/repositories/discover")
async def discover_repos(session: AsyncSession = Depends(get_session)):
    """Discover repositories in the repositories directory and register them"""
    discovered_paths = discover_repositories()
    registered = []

    for repo_path in discovered_paths:
        # Check if repo already exists
        result = await session.execute(
            select(Repository).where(Repository.name == repo_path.name)
        )
        existing = result.scalar_one_or_none()

        if not existing:
            # Initialize git analyzer to get repo info
            try:
                git_analyzer = GitAnalyzer(repo_path)
                if git_analyzer.open():
                    repo_info = git_analyzer.get_repo_info()
                    new_repo = Repository(
                        name=repo_path.name,
                        path=str(repo_path),
                        url=repo_info.url,
                        default_branch=repo_info.default_branch,
                        total_branches=len(repo_info.branches),
                        total_commits=0,
                        total_contributors=0
                    )
                    session.add(new_repo)
                    registered.append(repo_path.name)
                    git_analyzer.close()
                else:
                    logger.warning(f"Could not open repository: {repo_path}")
            except Exception as e:
                logger.error(f"Error registering {repo_path.name}: {e}")
        else:
            registered.append(repo_path.name)

    await session.commit()

    return {
        "discovered": [{"name": r.name, "path": str(r)} for r in discovered_paths],
        "registered": registered,
        "count": len(discovered_paths)
    }


@router.get("/repositories/{name}", response_model=RepositoryResponse)
async def get_repository(name: str, session: AsyncSession = Depends(get_session)):
    """Get repository details"""
    result = await session.execute(
        select(Repository).where(Repository.name == name)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.post("/repositories/{name}/analyze")
async def analyze_repository(
    name: str,
    background_tasks: BackgroundTasks,
    use_llm: bool = True,
    session: AsyncSession = Depends(get_session)
):
    """Trigger analysis for a repository"""
    repo_path = config.REPOSITORIES_DIR / name

    if not repo_path.exists():
        raise HTTPException(status_code=404, detail=f"Repository directory not found: {name}")

    # Check if analysis is already running
    result = await session.execute(
        select(AnalysisRun)
        .where(AnalysisRun.status == "running")
        .order_by(AnalysisRun.created_at.desc())
        .limit(1)
    )
    running = result.scalar_one_or_none()
    if running:
        raise HTTPException(status_code=409, detail="Analysis already in progress")

    # Create analysis run
    analysis_run = AnalysisRun(status="pending")
    session.add(analysis_run)
    await session.commit()
    await session.refresh(analysis_run)

    # Start background analysis
    background_tasks.add_task(
        run_analysis,
        repo_path,
        analysis_run.id,
        use_llm
    )

    return {"message": f"Analysis started for {name}", "run_id": analysis_run.id}


@router.post("/analyze/all")
async def analyze_all_repositories(
    background_tasks: BackgroundTasks,
    use_llm: bool = True,
    session: AsyncSession = Depends(get_session)
):
    """Analyze all repositories"""
    repos = discover_repositories()
    if not repos:
        raise HTTPException(status_code=404, detail="No repositories found")

    # Create analysis run
    analysis_run = AnalysisRun(status="pending")
    session.add(analysis_run)
    await session.commit()
    await session.refresh(analysis_run)

    background_tasks.add_task(
        run_analysis_all,
        repos,
        analysis_run.id,
        use_llm
    )

    return {
        "message": f"Analysis started for {len(repos)} repositories",
        "repositories": [r.name for r in repos],
        "run_id": analysis_run.id
    }


# ============== Contributor Endpoints ==============

@router.get("/contributors", response_model=List[ContributorResponse])
async def list_contributors(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_session)
):
    """List all contributors"""
    result = await session.execute(
        select(Contributor)
        .order_by(Contributor.impact_score.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/contributors/{email}", response_model=ContributorResponse)
async def get_contributor(email: str, session: AsyncSession = Depends(get_session)):
    """Get contributor details"""
    result = await session.execute(
        select(Contributor).where(Contributor.email == email.lower())
    )
    contributor = result.scalar_one_or_none()
    if not contributor:
        raise HTTPException(status_code=404, detail="Contributor not found")
    return contributor


# ============== Leaderboard Endpoints ==============

@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def global_leaderboard(
    limit: int = 20,
    session: AsyncSession = Depends(get_session)
):
    """Get global contributor leaderboard"""
    result = await session.execute(
        select(Contributor)
        .order_by(Contributor.impact_score.desc())
        .limit(limit)
    )
    contributors = result.scalars().all()

    return [
        LeaderboardEntry(
            rank=i + 1,
            email=c.email,
            name=c.name,
            commits=c.total_commits,
            lines_changed=c.total_lines_added + c.total_lines_removed,
            prs=c.total_prs,
            quality_score=round(c.quality_score, 1),
            impact_score=round(c.impact_score, 1)
        )
        for i, c in enumerate(contributors)
    ]


@router.get("/leaderboard/{repo_name}", response_model=List[LeaderboardEntry])
async def repository_leaderboard(
    repo_name: str,
    limit: int = 20,
    session: AsyncSession = Depends(get_session)
):
    """Get per-repository contributor leaderboard"""
    # Get repository
    result = await session.execute(
        select(Repository).where(Repository.name == repo_name)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get stats
    result = await session.execute(
        select(ContributorStats, Contributor)
        .join(Contributor, ContributorStats.contributor_id == Contributor.id)
        .where(ContributorStats.repository_id == repo.id)
        .order_by(ContributorStats.impact_score.desc())
        .limit(limit)
    )
    rows = result.all()

    return [
        LeaderboardEntry(
            rank=i + 1,
            email=contributor.email,
            name=contributor.name,
            commits=stats.commits,
            lines_changed=stats.lines_added + stats.lines_removed,
            prs=stats.prs,
            quality_score=round(stats.quality_score, 1),
            impact_score=round(stats.impact_score, 1)
        )
        for i, (stats, contributor) in enumerate(rows)
    ]


# ============== Status Endpoints ==============

@router.get("/status")
async def analysis_status(session: AsyncSession = Depends(get_session)):
    """Get current analysis status"""
    result = await session.execute(
        select(AnalysisRun)
        .order_by(AnalysisRun.created_at.desc())
        .limit(5)
    )
    runs = result.scalars().all()

    return {
        "runs": [
            {
                "id": r.id,
                "status": r.status,
                "commits_analyzed": r.commits_analyzed,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "error": r.error_message
            }
            for r in runs
        ]
    }


@router.get("/status/ollama", response_model=OllamaStatus)
async def ollama_status():
    """Check Ollama availability"""
    client = OllamaClient()
    available = await client.is_available()
    return OllamaStatus(
        available=available,
        host=config.OLLAMA_HOST,
        model=config.OLLAMA_MODEL
    )


@router.get("/stats")
async def global_stats(session: AsyncSession = Depends(get_session)):
    """Get global statistics"""
    # Repository count
    repo_count = await session.execute(select(func.count(Repository.id)))

    # Contributor count
    contrib_count = await session.execute(select(func.count(Contributor.id)))

    # Commit count
    commit_count = await session.execute(select(func.count(Commit.id)))

    # Average quality
    avg_quality = await session.execute(select(func.avg(Contributor.quality_score)))

    return {
        "total_repositories": repo_count.scalar() or 0,
        "total_contributors": contrib_count.scalar() or 0,
        "total_commits": commit_count.scalar() or 0,
        "average_quality_score": round(avg_quality.scalar() or 0, 1)
    }


# ============== Scoring Endpoints ==============

@router.get("/scores/repository/{repo_name}")
async def get_repository_score(repo_name: str, session: AsyncSession = Depends(get_session)):
    """Get comprehensive score for a single repository"""
    from app.analyzer.scoring import RepositoryScore, ScoringEngine
    from datetime import timedelta

    # Get repository
    result = await session.execute(
        select(Repository).where(Repository.name == repo_name)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get commits
    result = await session.execute(
        select(Commit).where(Commit.repository_id == repo.id)
    )
    commits = result.scalars().all()

    # Get contributor stats for this repo
    result = await session.execute(
        select(ContributorStats).where(ContributorStats.repository_id == repo.id)
    )
    stats = result.scalars().all()

    # Calculate score
    repo_data = {
        "name": repo.name,
        "total_commits": repo.total_commits,
        "total_contributors": repo.total_contributors,
        "total_branches": repo.total_branches,
    }

    commit_data = [
        {
            "committed_at": c.committed_at,
            "lines_added": c.lines_added,
            "lines_removed": c.lines_removed,
            "is_pr": c.is_pr,
            "contributor_email": "",
        }
        for c in commits
    ]

    contributor_data = [
        {"quality_score": s.quality_score}
        for s in stats
    ]

    score = await ScoringEngine.calculate_repository_score(
        repo_data, commit_data, contributor_data
    )

    return score.to_dict()


@router.get("/scores/global")
async def get_global_score(session: AsyncSession = Depends(get_session)):
    """Get comprehensive score across all repositories"""
    from app.analyzer.scoring import RepositoryScore, GlobalScore, ScoringEngine

    # Get all repositories
    result = await session.execute(select(Repository))
    repos = result.scalars().all()

    if not repos:
        return {
            "summary": {
                "total_repositories": 0,
                "total_commits": 0,
                "total_contributors": 0,
            },
            "scores": {
                "activity": 0,
                "health": 0,
                "quality": 0,
                "diversity": 0,
                "overall": 0,
            },
            "grade": "N/A",
            "repositories": [],
        }

    repo_scores = []

    for repo in repos:
        # Get commits for this repo
        result = await session.execute(
            select(Commit).where(Commit.repository_id == repo.id)
        )
        commits = result.scalars().all()

        # Get contributor stats
        result = await session.execute(
            select(ContributorStats).where(ContributorStats.repository_id == repo.id)
        )
        stats = result.scalars().all()

        repo_data = {
            "name": repo.name,
            "total_commits": repo.total_commits,
            "total_contributors": repo.total_contributors,
            "total_branches": repo.total_branches,
        }

        commit_data = [
            {
                "committed_at": c.committed_at,
                "lines_added": c.lines_added,
                "lines_removed": c.lines_removed,
                "is_pr": c.is_pr,
                "contributor_email": "",
            }
            for c in commits
        ]

        contributor_data = [
            {"quality_score": s.quality_score}
            for s in stats
        ]

        score = await ScoringEngine.calculate_repository_score(
            repo_data, commit_data, contributor_data
        )
        repo_scores.append(score)

    # Calculate global score
    global_score = ScoringEngine.calculate_global_score(repo_scores)

    return global_score.to_dict()


@router.get("/scores/summary")
async def get_scores_summary(session: AsyncSession = Depends(get_session)):
    """Get a quick summary of all scores"""
    from app.analyzer.scoring import ScoringEngine

    # Get all repositories with basic stats
    result = await session.execute(select(Repository))
    repos = result.scalars().all()

    repo_summaries = []
    total_score = 0

    for repo in repos:
        # Quick score calculation
        result = await session.execute(
            select(ContributorStats).where(ContributorStats.repository_id == repo.id)
        )
        stats = result.scalars().all()

        avg_quality = sum(s.quality_score for s in stats) / len(stats) if stats else 50

        # Simple score estimation
        activity = min(100, repo.total_commits * 0.1) if repo.total_commits else 0
        collab = min(100, repo.total_contributors * 10) if repo.total_contributors else 0
        overall = (activity * 0.3 + avg_quality * 0.4 + collab * 0.3)

        repo_summaries.append({
            "name": repo.name,
            "commits": repo.total_commits,
            "contributors": repo.total_contributors,
            "quality_score": round(avg_quality, 1),
            "overall_score": round(overall, 1),
            "grade": _score_to_grade(overall),
        })

        total_score += overall

    global_overall = total_score / len(repos) if repos else 0

    return {
        "global": {
            "total_repositories": len(repos),
            "overall_score": round(global_overall, 1),
            "grade": _score_to_grade(global_overall),
        },
        "repositories": sorted(repo_summaries, key=lambda x: x["overall_score"], reverse=True),
    }


def _score_to_grade(score: float) -> str:
    """Convert score to letter grade"""
    if score >= 90: return "A+"
    elif score >= 85: return "A"
    elif score >= 80: return "A-"
    elif score >= 75: return "B+"
    elif score >= 70: return "B"
    elif score >= 65: return "B-"
    elif score >= 60: return "C+"
    elif score >= 55: return "C"
    elif score >= 50: return "C-"
    elif score >= 45: return "D+"
    elif score >= 40: return "D"
    else: return "F"


# ============== Background Analysis Task ==============

async def run_analysis(repo_path: Path, run_id: int, use_llm: bool = True):
    """Run analysis for a single repository"""
    from app.models.database import SessionLocal

    async with SessionLocal() as session:
        # Update run status
        result = await session.execute(
            select(AnalysisRun).where(AnalysisRun.id == run_id)
        )
        run = result.scalar_one()
        run.status = "running"
        run.started_at = datetime.utcnow()
        await session.commit()

        try:
            # Initialize analyzers
            git_analyzer = GitAnalyzer(repo_path)
            if not git_analyzer.open():
                raise Exception(f"Failed to open repository: {repo_path}")

            repo_info = git_analyzer.get_repo_info()
            contrib_analyzer = ContributorAnalyzer()
            quality_analyzer = QualityAnalyzer()

            # Get or create repository record
            result = await session.execute(
                select(Repository).where(Repository.name == repo_path.name)
            )
            repo = result.scalar_one_or_none()
            if not repo:
                repo = Repository(
                    name=repo_path.name,
                    path=str(repo_path),
                    url=repo_info.url,
                    default_branch=repo_info.default_branch
                )
                session.add(repo)
                await session.commit()
                await session.refresh(repo)

            run.repository_id = repo.id

            # Process commits
            commits_analyzed = 0
            commit_infos = []

            for commit_info in git_analyzer.iter_all_commits():
                commit_infos.append(commit_info)
                commits_analyzed += 1

                if commits_analyzed % 100 == 0:
                    run.commits_analyzed = commits_analyzed
                    await session.commit()

            # Quality analysis on sample
            quality_reports = {}
            if use_llm:
                reports = await quality_analyzer.analyze_sample(
                    commit_infos,
                    sample_size=min(50, len(commit_infos))
                )
                quality_reports = {r.sha: r.overall_score for r in reports}

            # Process contributor metrics
            for commit_info in commit_infos:
                quality_score = quality_reports.get(commit_info.sha)
                contrib_analyzer.process_commit(commit_info, quality_score)

                # Get or create contributor
                result = await session.execute(
                    select(Contributor).where(Contributor.email == commit_info.author_email.lower())
                )
                contributor = result.scalar_one_or_none()
                if not contributor:
                    contributor = Contributor(
                        email=commit_info.author_email.lower(),
                        name=commit_info.author_name
                    )
                    session.add(contributor)
                    await session.commit()
                    await session.refresh(contributor)

                # Save commit
                commit_record = Commit(
                    sha=commit_info.sha,
                    repository_id=repo.id,
                    contributor_id=contributor.id,
                    message=commit_info.message[:1000] if commit_info.message else None,
                    branch=commit_info.branch,
                    lines_added=commit_info.lines_added,
                    lines_removed=commit_info.lines_removed,
                    files_changed=commit_info.files_changed,
                    is_merge=commit_info.is_merge,
                    is_pr=commit_info.is_pr,
                    quality_score=quality_score,
                    committed_at=commit_info.committed_at
                )
                session.add(commit_record)

            # Update contributor stats
            for email, metrics in contrib_analyzer.contributors.items():
                result = await session.execute(
                    select(Contributor).where(Contributor.email == email)
                )
                contributor = result.scalar_one()

                # Update global stats
                contributor.total_commits = metrics.commits
                contributor.total_lines_added = metrics.lines_added
                contributor.total_lines_removed = metrics.lines_removed
                contributor.total_prs = metrics.prs
                contributor.quality_score = metrics.average_quality
                contributor.impact_score = metrics.impact_score
                contributor.first_commit = metrics.first_commit
                contributor.last_commit = metrics.last_commit

                # Create/update per-repo stats
                result = await session.execute(
                    select(ContributorStats)
                    .where(ContributorStats.contributor_id == contributor.id)
                    .where(ContributorStats.repository_id == repo.id)
                )
                stats = result.scalar_one_or_none()
                if not stats:
                    stats = ContributorStats(
                        contributor_id=contributor.id,
                        repository_id=repo.id
                    )
                    session.add(stats)

                stats.commits = metrics.commits
                stats.lines_added = metrics.lines_added
                stats.lines_removed = metrics.lines_removed
                stats.prs = metrics.prs
                stats.branches_touched = metrics.branches_count
                stats.quality_score = metrics.average_quality
                stats.impact_score = metrics.impact_score
                stats.first_commit = metrics.first_commit
                stats.last_commit = metrics.last_commit
                stats.commit_frequency = metrics.commit_frequency

            # Update repository stats
            repo.total_commits = commits_analyzed
            repo.total_contributors = len(contrib_analyzer.contributors)
            repo.total_branches = len(repo_info.branches)
            repo.last_analyzed = datetime.utcnow()

            # Update rankings
            rankings = contrib_analyzer.get_rankings()
            for rank, metrics in enumerate(rankings, 1):
                result = await session.execute(
                    select(ContributorStats)
                    .join(Contributor)
                    .where(Contributor.email == metrics.email)
                    .where(ContributorStats.repository_id == repo.id)
                )
                stats = result.scalar_one_or_none()
                if stats:
                    stats.rank = rank

            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.commits_analyzed = commits_analyzed

            await session.commit()
            git_analyzer.close()

            logger.info(f"Analysis completed for {repo_path.name}: {commits_analyzed} commits")

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            await session.commit()


async def run_analysis_all(repos: List[Path], run_id: int, use_llm: bool = True):
    """Run analysis for all repositories"""
    for repo_path in repos:
        await run_analysis(repo_path, run_id, use_llm)
