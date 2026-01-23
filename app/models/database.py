"""Database models and connection handling"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey,
    Boolean, create_engine, Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker as async_sessionmaker

import config

Base = declarative_base()


class Repository(Base):
    """Git repository being analyzed"""
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    path = Column(String(1024), nullable=False)
    url = Column(String(1024), nullable=True)
    default_branch = Column(String(255), default="main")
    total_commits = Column(Integer, default=0)
    total_contributors = Column(Integer, default=0)
    total_branches = Column(Integer, default=0)
    last_analyzed = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")
    contributor_stats = relationship("ContributorStats", back_populates="repository", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_repo_name", "name"),
    )


class Contributor(Base):
    """Individual contributor across all repositories"""
    __tablename__ = "contributors"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(1024), nullable=True)
    total_commits = Column(Integer, default=0)
    total_lines_added = Column(Integer, default=0)
    total_lines_removed = Column(Integer, default=0)
    total_files_changed = Column(Integer, default=0)
    total_prs = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0)
    impact_score = Column(Float, default=0.0)
    pr_quality_score = Column(Float, default=0.0)
    pr_prs_analyzed = Column(Integer, default=0)
    first_commit = Column(DateTime, nullable=True)
    last_commit = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    commits = relationship("Commit", back_populates="contributor")
    stats = relationship("ContributorStats", back_populates="contributor")

    __table_args__ = (
        Index("idx_contributor_email", "email"),
        Index("idx_contributor_impact", "impact_score"),
    )


class Commit(Base):
    """Individual commit record"""
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True)
    sha = Column(String(40), nullable=False)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    contributor_id = Column(Integer, ForeignKey("contributors.id"), nullable=False)
    message = Column(Text, nullable=True)
    branch = Column(String(255), nullable=True)
    lines_added = Column(Integer, default=0)
    lines_removed = Column(Integer, default=0)
    files_changed = Column(Integer, default=0)
    is_merge = Column(Boolean, default=False)
    is_pr = Column(Boolean, default=False)
    quality_score = Column(Float, nullable=True)
    committed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    repository = relationship("Repository", back_populates="commits")
    contributor = relationship("Contributor", back_populates="commits")

    __table_args__ = (
        Index("idx_commit_sha", "sha"),
        Index("idx_commit_repo", "repository_id"),
        Index("idx_commit_contributor", "contributor_id"),
        Index("idx_commit_date", "committed_at"),
    )


class ContributorStats(Base):
    """Per-repository contributor statistics"""
    __tablename__ = "contributor_stats"

    id = Column(Integer, primary_key=True)
    contributor_id = Column(Integer, ForeignKey("contributors.id"), nullable=False)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    commits = Column(Integer, default=0)
    lines_added = Column(Integer, default=0)
    lines_removed = Column(Integer, default=0)
    files_changed = Column(Integer, default=0)
    prs = Column(Integer, default=0)
    branches_touched = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0)
    impact_score = Column(Float, default=0.0)
    pr_quality_score = Column(Float, default=0.0)
    pr_prs_analyzed = Column(Integer, default=0)
    rank = Column(Integer, nullable=True)
    first_commit = Column(DateTime, nullable=True)
    last_commit = Column(DateTime, nullable=True)
    commit_frequency = Column(Float, default=0.0)  # commits per week
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contributor = relationship("Contributor", back_populates="stats")
    repository = relationship("Repository", back_populates="contributor_stats")

    __table_args__ = (
        Index("idx_stats_contributor", "contributor_id"),
        Index("idx_stats_repo", "repository_id"),
        Index("idx_stats_rank", "repository_id", "rank"),
    )


class AnalysisRun(Base):
    """Track analysis runs"""
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    commits_analyzed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CodebaseAnalysis(Base):
    """Static codebase analysis results per repository."""
    __tablename__ = "codebase_analyses"

    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, unique=True)
    overall_score = Column(Float, default=0.0)
    complexity_score = Column(Float, default=0.0)
    dependency_score = Column(Float, default=0.0)
    comment_score = Column(Float, default=0.0)
    test_score = Column(Float, default=0.0)
    metrics_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ContributorMerge(Base):
    """Represents a merged contributor mapping (merged -> primary)"""
    __tablename__ = "contributor_merges"

    id = Column(Integer, primary_key=True)
    primary_contributor_id = Column(Integer, ForeignKey("contributors.id"), nullable=False)
    merged_contributor_id = Column(Integer, ForeignKey("contributors.id"), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_merge_primary", "primary_contributor_id"),
        Index("idx_merge_merged", "merged_contributor_id", unique=True),
    )


# Database engine and session
engine = None
SessionLocal = None


async def init_db():
    """Initialize the database"""
    global engine, SessionLocal

    # Convert sqlite:// to sqlite+aiosqlite:// for async
    db_url = config.DATABASE_URL
    if db_url.startswith("sqlite://"):
        db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")

    engine = create_async_engine(db_url, echo=config.DEBUG)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_schema(conn, db_url)


async def _ensure_schema(conn, db_url: str) -> None:
    """Lightweight schema migration for SQLite."""
    if not db_url.startswith("sqlite"):
        return

    async def column_exists(table: str, column: str) -> bool:
        result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
        rows = result.fetchall()
        return any(row[1] == column for row in rows)

    # Contributors
    if not await column_exists("contributors", "pr_quality_score"):
        await conn.exec_driver_sql("ALTER TABLE contributors ADD COLUMN pr_quality_score FLOAT DEFAULT 0.0")
    if not await column_exists("contributors", "pr_prs_analyzed"):
        await conn.exec_driver_sql("ALTER TABLE contributors ADD COLUMN pr_prs_analyzed INTEGER DEFAULT 0")

    # Contributor stats
    if not await column_exists("contributor_stats", "pr_quality_score"):
        await conn.exec_driver_sql("ALTER TABLE contributor_stats ADD COLUMN pr_quality_score FLOAT DEFAULT 0.0")
    if not await column_exists("contributor_stats", "pr_prs_analyzed"):
        await conn.exec_driver_sql("ALTER TABLE contributor_stats ADD COLUMN pr_prs_analyzed INTEGER DEFAULT 0")


async def get_session() -> AsyncSession:
    """Get database session"""
    async with SessionLocal() as session:
        yield session
