"""Repository and Global Scoring Module"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RepositoryScore:
    """Comprehensive score for a single repository"""
    name: str

    # Activity metrics
    total_commits: int = 0
    total_contributors: int = 0
    total_branches: int = 0
    total_prs: int = 0
    total_lines_added: int = 0
    total_lines_removed: int = 0

    # Time-based metrics
    first_commit: Optional[datetime] = None
    last_commit: Optional[datetime] = None
    commits_last_30_days: int = 0
    commits_last_90_days: int = 0
    active_contributors_30_days: int = 0

    # Quality metrics
    avg_quality_score: float = 0.0
    avg_commit_message_score: float = 0.0

    # Calculated scores (0-100)
    activity_score: float = 0.0
    health_score: float = 0.0
    quality_score: float = 0.0
    collaboration_score: float = 0.0
    overall_score: float = 0.0

    # Grade (A-F)
    grade: str = "N/A"

    def calculate_scores(self):
        """Calculate all derived scores"""
        self.activity_score = self._calc_activity_score()
        self.health_score = self._calc_health_score()
        self.quality_score = self._calc_quality_score()
        self.collaboration_score = self._calc_collaboration_score()

        # Overall is weighted average
        self.overall_score = (
            self.activity_score * 0.25 +
            self.health_score * 0.25 +
            self.quality_score * 0.30 +
            self.collaboration_score * 0.20
        )

        self.grade = self._calc_grade(self.overall_score)

    def _calc_activity_score(self) -> float:
        """Score based on commit activity"""
        score = 0.0

        # Recent activity (last 30 days)
        if self.commits_last_30_days > 0:
            score += min(40, self.commits_last_30_days * 2)

        # Medium-term activity (last 90 days)
        if self.commits_last_90_days > 0:
            score += min(30, self.commits_last_90_days * 0.5)

        # Total commits (log scale)
        if self.total_commits > 0:
            score += min(30, math.log10(self.total_commits) * 15)

        return min(100, score)

    def _calc_health_score(self) -> float:
        """Score based on repository health indicators"""
        score = 50.0  # Base score

        # Active development
        if self.last_commit:
            days_since_commit = (datetime.utcnow() - self.last_commit.replace(tzinfo=None)).days
            if days_since_commit <= 7:
                score += 25
            elif days_since_commit <= 30:
                score += 15
            elif days_since_commit <= 90:
                score += 5
            else:
                score -= 15

        # Multiple branches (active development)
        if self.total_branches > 1:
            score += min(15, self.total_branches * 3)

        # PR usage
        if self.total_prs > 0 and self.total_commits > 0:
            pr_ratio = self.total_prs / self.total_commits
            score += min(10, pr_ratio * 100)

        return max(0, min(100, score))

    def _calc_quality_score(self) -> float:
        """Score based on code quality metrics"""
        if self.avg_quality_score > 0:
            return self.avg_quality_score

        # Fallback heuristics
        score = 50.0

        # Good commit message quality
        if self.avg_commit_message_score > 0:
            score = (score + self.avg_commit_message_score) / 2

        return score

    def _calc_collaboration_score(self) -> float:
        """Score based on collaboration metrics"""
        score = 0.0

        # Multiple contributors
        if self.total_contributors >= 10:
            score += 40
        elif self.total_contributors >= 5:
            score += 30
        elif self.total_contributors >= 2:
            score += 20
        else:
            score += 10

        # Active contributors recently
        if self.active_contributors_30_days > 0:
            score += min(30, self.active_contributors_30_days * 10)

        # PR workflow usage
        if self.total_prs > 0:
            score += min(30, self.total_prs * 2)

        return min(100, score)

    def _calc_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return "A+"
        elif score >= 85:
            return "A"
        elif score >= 80:
            return "A-"
        elif score >= 75:
            return "B+"
        elif score >= 70:
            return "B"
        elif score >= 65:
            return "B-"
        elif score >= 60:
            return "C+"
        elif score >= 55:
            return "C"
        elif score >= 50:
            return "C-"
        elif score >= 45:
            return "D+"
        elif score >= 40:
            return "D"
        else:
            return "F"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            "name": self.name,
            "metrics": {
                "total_commits": self.total_commits,
                "total_contributors": self.total_contributors,
                "total_branches": self.total_branches,
                "total_prs": self.total_prs,
                "total_lines_added": self.total_lines_added,
                "total_lines_removed": self.total_lines_removed,
                "commits_last_30_days": self.commits_last_30_days,
                "commits_last_90_days": self.commits_last_90_days,
                "active_contributors_30_days": self.active_contributors_30_days,
            },
            "scores": {
                "activity": round(self.activity_score, 1),
                "health": round(self.health_score, 1),
                "quality": round(self.quality_score, 1),
                "collaboration": round(self.collaboration_score, 1),
                "overall": round(self.overall_score, 1),
            },
            "grade": self.grade,
            "first_commit": self.first_commit.isoformat() if self.first_commit else None,
            "last_commit": self.last_commit.isoformat() if self.last_commit else None,
        }


@dataclass
class GlobalScore:
    """Aggregated score across all repositories"""

    # Counts
    total_repositories: int = 0
    total_commits: int = 0
    total_contributors: int = 0
    total_prs: int = 0
    total_lines_added: int = 0
    total_lines_removed: int = 0

    # Averages across repos
    avg_commits_per_repo: float = 0.0
    avg_contributors_per_repo: float = 0.0
    avg_quality_score: float = 0.0

    # Activity
    active_repos_30_days: int = 0
    total_commits_30_days: int = 0

    # Individual repo scores
    repo_scores: List[RepositoryScore] = field(default_factory=list)

    # Calculated scores (0-100)
    portfolio_activity_score: float = 0.0
    portfolio_health_score: float = 0.0
    portfolio_quality_score: float = 0.0
    portfolio_diversity_score: float = 0.0
    overall_score: float = 0.0

    # Grade
    grade: str = "N/A"

    def calculate_scores(self):
        """Calculate global scores from repository scores"""
        if not self.repo_scores:
            return

        # Aggregate from repos
        self.total_repositories = len(self.repo_scores)
        self.total_commits = sum(r.total_commits for r in self.repo_scores)
        self.total_prs = sum(r.total_prs for r in self.repo_scores)
        self.total_lines_added = sum(r.total_lines_added for r in self.repo_scores)
        self.total_lines_removed = sum(r.total_lines_removed for r in self.repo_scores)
        self.total_commits_30_days = sum(r.commits_last_30_days for r in self.repo_scores)

        # Count unique contributors (approximation - sum of per-repo)
        self.total_contributors = sum(r.total_contributors for r in self.repo_scores)

        # Averages
        self.avg_commits_per_repo = self.total_commits / self.total_repositories
        self.avg_contributors_per_repo = self.total_contributors / self.total_repositories
        self.avg_quality_score = sum(r.quality_score for r in self.repo_scores) / self.total_repositories

        # Active repos
        self.active_repos_30_days = sum(1 for r in self.repo_scores if r.commits_last_30_days > 0)

        # Calculate portfolio scores
        self.portfolio_activity_score = self._calc_portfolio_activity()
        self.portfolio_health_score = self._calc_portfolio_health()
        self.portfolio_quality_score = self._calc_portfolio_quality()
        self.portfolio_diversity_score = self._calc_portfolio_diversity()

        # Overall
        self.overall_score = (
            self.portfolio_activity_score * 0.25 +
            self.portfolio_health_score * 0.25 +
            self.portfolio_quality_score * 0.30 +
            self.portfolio_diversity_score * 0.20
        )

        self.grade = self._calc_grade(self.overall_score)

    def _calc_portfolio_activity(self) -> float:
        """Average activity across repos"""
        if not self.repo_scores:
            return 0.0
        return sum(r.activity_score for r in self.repo_scores) / len(self.repo_scores)

    def _calc_portfolio_health(self) -> float:
        """Average health across repos"""
        if not self.repo_scores:
            return 0.0
        return sum(r.health_score for r in self.repo_scores) / len(self.repo_scores)

    def _calc_portfolio_quality(self) -> float:
        """Average quality across repos"""
        if not self.repo_scores:
            return 0.0
        return sum(r.quality_score for r in self.repo_scores) / len(self.repo_scores)

    def _calc_portfolio_diversity(self) -> float:
        """Score based on diversity of contributions"""
        score = 0.0

        # Multiple repos
        if self.total_repositories >= 10:
            score += 40
        elif self.total_repositories >= 5:
            score += 30
        elif self.total_repositories >= 2:
            score += 20
        else:
            score += 10

        # Active ratio
        if self.total_repositories > 0:
            active_ratio = self.active_repos_30_days / self.total_repositories
            score += active_ratio * 40

        # Contributor spread
        if self.avg_contributors_per_repo >= 5:
            score += 20
        elif self.avg_contributors_per_repo >= 2:
            score += 10

        return min(100, score)

    def _calc_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return "A+"
        elif score >= 85:
            return "A"
        elif score >= 80:
            return "A-"
        elif score >= 75:
            return "B+"
        elif score >= 70:
            return "B"
        elif score >= 65:
            return "B-"
        elif score >= 60:
            return "C+"
        elif score >= 55:
            return "C"
        elif score >= 50:
            return "C-"
        elif score >= 45:
            return "D+"
        elif score >= 40:
            return "D"
        else:
            return "F"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            "summary": {
                "total_repositories": self.total_repositories,
                "total_commits": self.total_commits,
                "total_contributors": self.total_contributors,
                "total_prs": self.total_prs,
                "total_lines_changed": self.total_lines_added + self.total_lines_removed,
                "active_repos_30_days": self.active_repos_30_days,
                "total_commits_30_days": self.total_commits_30_days,
            },
            "averages": {
                "commits_per_repo": round(self.avg_commits_per_repo, 1),
                "contributors_per_repo": round(self.avg_contributors_per_repo, 1),
                "quality_score": round(self.avg_quality_score, 1),
            },
            "scores": {
                "activity": round(self.portfolio_activity_score, 1),
                "health": round(self.portfolio_health_score, 1),
                "quality": round(self.portfolio_quality_score, 1),
                "diversity": round(self.portfolio_diversity_score, 1),
                "overall": round(self.overall_score, 1),
            },
            "grade": self.grade,
            "repositories": [r.to_dict() for r in self.repo_scores],
        }


class ScoringEngine:
    """Calculate scores for repositories"""

    @staticmethod
    async def calculate_repository_score(
        repo_data: Dict,
        commits: List[Dict],
        contributors: List[Dict]
    ) -> RepositoryScore:
        """Calculate score for a single repository"""

        score = RepositoryScore(name=repo_data.get("name", "unknown"))

        # Basic metrics
        score.total_commits = repo_data.get("total_commits", 0)
        score.total_contributors = repo_data.get("total_contributors", 0)
        score.total_branches = repo_data.get("total_branches", 0)

        # Calculate from commits
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)
        ninety_days_ago = now - timedelta(days=90)

        active_contributors_30 = set()

        for commit in commits:
            committed_at = commit.get("committed_at")
            if isinstance(committed_at, str):
                committed_at = datetime.fromisoformat(committed_at.replace("Z", "+00:00"))

            if committed_at:
                committed_at_naive = committed_at.replace(tzinfo=None) if committed_at.tzinfo else committed_at

                if score.first_commit is None or committed_at_naive < score.first_commit:
                    score.first_commit = committed_at_naive
                if score.last_commit is None or committed_at_naive > score.last_commit:
                    score.last_commit = committed_at_naive

                if committed_at_naive >= thirty_days_ago:
                    score.commits_last_30_days += 1
                    active_contributors_30.add(commit.get("contributor_email", ""))

                if committed_at_naive >= ninety_days_ago:
                    score.commits_last_90_days += 1

            score.total_lines_added += commit.get("lines_added", 0)
            score.total_lines_removed += commit.get("lines_removed", 0)

            if commit.get("is_pr"):
                score.total_prs += 1

        score.active_contributors_30_days = len(active_contributors_30)

        # Quality scores from contributors
        quality_scores = [c.get("quality_score", 0) for c in contributors if c.get("quality_score")]
        if quality_scores:
            score.avg_quality_score = sum(quality_scores) / len(quality_scores)

        # Calculate derived scores
        score.calculate_scores()

        return score

    @staticmethod
    def calculate_global_score(repo_scores: List[RepositoryScore]) -> GlobalScore:
        """Calculate global score from all repository scores"""
        global_score = GlobalScore()
        global_score.repo_scores = repo_scores
        global_score.calculate_scores()
        return global_score
