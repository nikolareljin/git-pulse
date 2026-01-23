"""Git Repository Analyzer"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Generator
from dataclasses import dataclass, field

from git import Repo, Commit as GitCommit
from git.exc import InvalidGitRepositoryError, GitCommandError

import config

logger = logging.getLogger(__name__)


@dataclass
class CommitInfo:
    """Parsed commit information"""
    sha: str
    author_name: str
    author_email: str
    message: str
    committed_at: datetime
    branch: str
    lines_added: int = 0
    lines_removed: int = 0
    files_changed: int = 0
    is_merge: bool = False
    is_pr: bool = False
    diff_content: str = ""


@dataclass
class BranchInfo:
    """Branch information"""
    name: str
    commit_count: int
    last_commit: datetime
    is_default: bool = False


@dataclass
class RepoInfo:
    """Repository information"""
    name: str
    path: str
    url: Optional[str]
    default_branch: str
    branches: List[BranchInfo] = field(default_factory=list)
    total_commits: int = 0


class GitAnalyzer:
    """Analyzes Git repositories"""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.repo: Optional[Repo] = None

    def open(self) -> bool:
        """Open the repository"""
        try:
            self.repo = Repo(self.repo_path)
            return True
        except InvalidGitRepositoryError:
            logger.error(f"Invalid git repository: {self.repo_path}")
            return False
        except Exception as e:
            logger.error(f"Error opening repository: {e}")
            return False

    def close(self):
        """Close the repository"""
        if self.repo:
            self.repo.close()
            self.repo = None

    def get_repo_info(self) -> Optional[RepoInfo]:
        """Get repository information"""
        if not self.repo:
            return None

        try:
            # Get remote URL if available
            url = None
            if self.repo.remotes:
                try:
                    url = self.repo.remotes.origin.url
                except AttributeError:
                    pass

            # Get default branch
            try:
                default_branch = self.repo.active_branch.name
            except TypeError:
                default_branch = "main"

            # Get branches
            branches = []
            for branch in self.repo.branches:
                try:
                    commit_count = sum(1 for _ in self.repo.iter_commits(branch.name, max_count=1000))
                    last_commit = branch.commit.committed_datetime
                    branches.append(BranchInfo(
                        name=branch.name,
                        commit_count=commit_count,
                        last_commit=last_commit,
                        is_default=(branch.name == default_branch)
                    ))
                except Exception as e:
                    logger.warning(f"Error processing branch {branch.name}: {e}")

            return RepoInfo(
                name=self.repo_path.name,
                path=str(self.repo_path),
                url=url,
                default_branch=default_branch,
                branches=branches,
                total_commits=sum(b.commit_count for b in branches)
            )
        except Exception as e:
            logger.error(f"Error getting repo info: {e}")
            return None

    def iter_all_commits(self, max_commits: int = None) -> Generator[CommitInfo, None, None]:
        """Iterate over all commits across all branches"""
        if not self.repo:
            return

        max_commits = max_commits or config.MAX_COMMITS_PER_REPO
        seen_shas = set()
        commit_count = 0

        # Iterate through all branches
        for branch in self.repo.branches:
            try:
                for commit in self.repo.iter_commits(branch.name):
                    if commit.hexsha in seen_shas:
                        continue

                    if commit_count >= max_commits:
                        return

                    seen_shas.add(commit.hexsha)
                    commit_count += 1

                    commit_info = self._parse_commit(commit, branch.name)
                    if commit_info:
                        yield commit_info

            except Exception as e:
                logger.warning(f"Error iterating branch {branch.name}: {e}")
                continue

    def _parse_commit(self, commit: GitCommit, branch: str) -> Optional[CommitInfo]:
        """Parse a git commit into CommitInfo"""
        try:
            # Get diff stats
            lines_added = 0
            lines_removed = 0
            files_changed = 0
            diff_content = ""

            try:
                if commit.parents:
                    diff = commit.parents[0].diff(commit, create_patch=True)
                    for d in diff:
                        files_changed += 1
                        if d.diff:
                            diff_text = d.diff.decode('utf-8', errors='ignore')
                            diff_content += diff_text[:config.MAX_DIFF_SIZE // len(diff) if diff else config.MAX_DIFF_SIZE]
                            for line in diff_text.split('\n'):
                                if line.startswith('+') and not line.startswith('+++'):
                                    lines_added += 1
                                elif line.startswith('-') and not line.startswith('---'):
                                    lines_removed += 1
            except Exception as e:
                logger.debug(f"Error getting diff for {commit.hexsha}: {e}")

            # Detect merge/PR commits
            is_merge = len(commit.parents) > 1
            message = commit.message.strip()
            is_pr = is_merge and any(
                pattern in message.lower()
                for pattern in ['merge pull request', 'merged pr', 'pull request #']
            )

            return CommitInfo(
                sha=commit.hexsha,
                author_name=commit.author.name,
                author_email=commit.author.email.lower(),
                message=message,
                committed_at=commit.committed_datetime,
                branch=branch,
                lines_added=lines_added,
                lines_removed=lines_removed,
                files_changed=files_changed,
                is_merge=is_merge,
                is_pr=is_pr,
                diff_content=diff_content[:config.MAX_DIFF_SIZE]
            )
        except Exception as e:
            logger.warning(f"Error parsing commit {commit.hexsha}: {e}")
            return None

    def get_commit_by_sha(self, sha: str) -> Optional[CommitInfo]:
        """Get a specific commit by SHA"""
        if not self.repo:
            return None

        try:
            commit = self.repo.commit(sha)
            return self._parse_commit(commit, "unknown")
        except Exception as e:
            logger.error(f"Error getting commit {sha}: {e}")
            return None


def discover_repositories() -> List[Path]:
    """Discover all git repositories in the repositories directory"""
    repos = []
    repos_dir = config.REPOSITORIES_DIR

    if not repos_dir.exists():
        logger.warning(f"Repositories directory does not exist: {repos_dir}")
        return repos

    for item in repos_dir.iterdir():
        if item.is_dir():
            git_dir = item / ".git"
            if git_dir.exists():
                repos.append(item)
                logger.info(f"Discovered repository: {item.name}")

    return repos
