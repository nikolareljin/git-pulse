"""Contributor Analysis Module"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from app.analyzer.git_analyzer import CommitInfo

logger = logging.getLogger(__name__)


@dataclass
class ContributorMetrics:
    """Aggregated metrics for a contributor"""
    email: str
    name: str
    commits: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    files_changed: int = 0
    prs: int = 0
    branches: set = field(default_factory=set)
    first_commit: Optional[datetime] = None
    last_commit: Optional[datetime] = None
    quality_scores: List[float] = field(default_factory=list)
    commit_dates: List[datetime] = field(default_factory=list)

    @property
    def branches_count(self) -> int:
        return len(self.branches)

    @property
    def net_lines(self) -> int:
        return self.lines_added - self.lines_removed

    @property
    def average_quality(self) -> float:
        if not self.quality_scores:
            return 50.0
        return sum(self.quality_scores) / len(self.quality_scores)

    @property
    def commit_frequency(self) -> float:
        """Calculate commits per week"""
        if not self.first_commit or not self.last_commit:
            return 0.0
        if self.first_commit == self.last_commit:
            return self.commits

        days = (self.last_commit - self.first_commit).days
        if days <= 0:
            return self.commits
        weeks = max(1, days / 7)
        return self.commits / weeks

    @property
    def impact_score(self) -> float:
        """Calculate overall impact score (0-100)"""
        # Weighted factors
        commit_weight = 0.25
        lines_weight = 0.20
        quality_weight = 0.25
        consistency_weight = 0.15
        pr_weight = 0.15

        # Normalize commits (log scale, cap at ~1000)
        import math
        commit_score = min(100, math.log10(max(1, self.commits)) * 33)

        # Normalize lines changed (log scale)
        total_lines = self.lines_added + self.lines_removed
        lines_score = min(100, math.log10(max(1, total_lines)) * 20)

        # Quality score
        quality_score = self.average_quality

        # Consistency score (based on commit frequency and duration)
        if self.first_commit and self.last_commit:
            active_days = (self.last_commit - self.first_commit).days
            consistency_score = min(100, (active_days / 30) * 10 + self.commit_frequency * 5)
        else:
            consistency_score = 0

        # PR contribution score
        pr_score = min(100, self.prs * 10)

        # Calculate weighted total
        impact = (
            commit_score * commit_weight +
            lines_score * lines_weight +
            quality_score * quality_weight +
            consistency_score * consistency_weight +
            pr_score * pr_weight
        )

        return round(min(100, max(0, impact)), 2)


class ContributorAnalyzer:
    """Analyzes contributor metrics from commits"""

    def __init__(self):
        self.contributors: Dict[str, ContributorMetrics] = {}

    def process_commit(self, commit: CommitInfo, quality_score: float = None):
        """Process a single commit and update contributor metrics"""
        email = commit.author_email.lower()

        if email not in self.contributors:
            self.contributors[email] = ContributorMetrics(
                email=email,
                name=commit.author_name
            )

        contrib = self.contributors[email]

        # Update counts
        contrib.commits += 1
        contrib.lines_added += commit.lines_added
        contrib.lines_removed += commit.lines_removed
        contrib.files_changed += commit.files_changed

        if commit.is_pr:
            contrib.prs += 1

        contrib.branches.add(commit.branch)

        # Update timestamps
        if contrib.first_commit is None or commit.committed_at < contrib.first_commit:
            contrib.first_commit = commit.committed_at
        if contrib.last_commit is None or commit.committed_at > contrib.last_commit:
            contrib.last_commit = commit.committed_at

        contrib.commit_dates.append(commit.committed_at)

        if quality_score is not None:
            contrib.quality_scores.append(quality_score)

    def get_rankings(self, limit: int = None) -> List[ContributorMetrics]:
        """Get contributors ranked by impact score"""
        ranked = sorted(
            self.contributors.values(),
            key=lambda c: c.impact_score,
            reverse=True
        )
        if limit:
            return ranked[:limit]
        return ranked

    def get_contributor(self, email: str) -> Optional[ContributorMetrics]:
        """Get metrics for a specific contributor"""
        return self.contributors.get(email.lower())

    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        if not self.contributors:
            return {
                "total_contributors": 0,
                "total_commits": 0,
                "total_lines_added": 0,
                "total_lines_removed": 0,
                "total_prs": 0,
                "average_quality": 0,
            }

        contributors = list(self.contributors.values())

        return {
            "total_contributors": len(contributors),
            "total_commits": sum(c.commits for c in contributors),
            "total_lines_added": sum(c.lines_added for c in contributors),
            "total_lines_removed": sum(c.lines_removed for c in contributors),
            "total_prs": sum(c.prs for c in contributors),
            "average_quality": sum(c.average_quality for c in contributors) / len(contributors),
            "top_contributor": max(contributors, key=lambda c: c.impact_score).email if contributors else None,
        }

    def clear(self):
        """Clear all contributor data"""
        self.contributors.clear()
