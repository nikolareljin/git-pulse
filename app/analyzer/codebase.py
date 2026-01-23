"""Static codebase analysis for repository quality."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

IGNORED_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", ".venv", "venv",
    ".tox", ".pytest_cache", ".mypy_cache", ".ruff_cache", "__pycache__",
    ".idea", ".vscode", "coverage", "logs", "data", "repositories",
}

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".php": "PHP",
    ".groovy": "Groovy",
    ".gradle": "Groovy",
    ".sh": "Bash",
    ".bash": "Bash",
}

COMPLEXITY_KEYWORDS = re.compile(r"\b(if|elif|for|while|case|catch|except)\b")
LOGICAL_OPERATORS = re.compile(r"(&&|\|\||\?\:)")


@dataclass
class CodebaseReport:
    """Aggregated repository codebase metrics."""
    total_files: int = 0
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    language_files: Dict[str, int] = field(default_factory=dict)
    language_code_lines: Dict[str, int] = field(default_factory=dict)
    complexity: int = 0
    complexity_score: float = 0.0
    dependency_score: float = 0.0
    comment_score: float = 0.0
    test_score: float = 0.0
    overall_score: float = 0.0
    dependency_warnings: List[str] = field(default_factory=list)
    test_files: int = 0

    def to_dict(self) -> Dict:
        return {
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "code_lines": self.code_lines,
            "comment_lines": self.comment_lines,
            "blank_lines": self.blank_lines,
            "language_files": self.language_files,
            "language_code_lines": self.language_code_lines,
            "complexity": self.complexity,
            "complexity_score": round(self.complexity_score, 1),
            "dependency_score": round(self.dependency_score, 1),
            "comment_score": round(self.comment_score, 1),
            "test_score": round(self.test_score, 1),
            "overall_score": round(self.overall_score, 1),
            "dependency_warnings": self.dependency_warnings,
            "test_files": self.test_files,
        }


def _detect_language(path: Path) -> str | None:
    if path.name == "Dockerfile" or path.name.endswith(".Dockerfile"):
        return "Docker"
    return LANGUAGE_EXTENSIONS.get(path.suffix.lower())


def _is_test_path(path: Path) -> bool:
    lowered = str(path).lower()
    if "/test" in lowered or "/tests" in lowered or "__tests__" in lowered:
        return True
    if lowered.endswith("_test.py") or lowered.endswith(".spec.js") or lowered.endswith(".spec.ts"):
        return True
    return False


def _count_lines(content: str, language: str) -> Tuple[int, int, int, int]:
    total = 0
    code = 0
    comments = 0
    blanks = 0

    in_block = False
    block_start = "/*"
    block_end = "*/"

    for raw in content.splitlines():
        total += 1
        line = raw.strip()
        if not line:
            blanks += 1
            continue

        if language in {"JavaScript", "TypeScript", "Groovy", "PHP"}:
            if in_block:
                comments += 1
                if block_end in line:
                    in_block = False
                continue
            if line.startswith("//") or line.startswith("#"):
                comments += 1
                continue
            if block_start in line:
                comments += 1
                if block_end not in line:
                    in_block = True
                continue
        elif language in {"Python", "Bash", "Docker"}:
            if line.startswith("#"):
                comments += 1
                continue

        code += 1

    return total, code, comments, blanks


def _complexity_for_content(content: str) -> int:
    complexity = 0
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        complexity += len(COMPLEXITY_KEYWORDS.findall(stripped))
        complexity += len(LOGICAL_OPERATORS.findall(stripped))
    return complexity


def _dependency_risk(repo_path: Path) -> Tuple[float, List[str]]:
    warnings: List[str] = []
    risk_points = 0

    package_json = repo_path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8", errors="ignore"))
            deps = {}
            deps.update(data.get("dependencies", {}))
            deps.update(data.get("devDependencies", {}))
            for name, version in deps.items():
                if isinstance(version, str) and (version in {"*", "latest"} or version.startswith("git") or version.startswith("http")):
                    risk_points += 2
                elif isinstance(version, str) and not version.startswith(("~", "^")) and not re.search(r"\d", version):
                    risk_points += 1
        except Exception:
            warnings.append("Unable to parse package.json")

        if not (repo_path / "package-lock.json").exists() and not (repo_path / "yarn.lock").exists() and not (repo_path / "pnpm-lock.yaml").exists():
            warnings.append("No JS lockfile detected")
            risk_points += 5

    requirements = repo_path / "requirements.txt"
    if requirements.exists():
        for line in requirements.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "==" not in stripped:
                risk_points += 1
        if not (repo_path / "requirements.lock").exists() and not (repo_path / "poetry.lock").exists() and not (repo_path / "Pipfile.lock").exists():
            warnings.append("No Python lockfile detected")
            risk_points += 4

    composer = repo_path / "composer.json"
    if composer.exists():
        try:
            data = json.loads(composer.read_text(encoding="utf-8", errors="ignore"))
            deps = {}
            deps.update(data.get("require", {}))
            deps.update(data.get("require-dev", {}))
            for name, version in deps.items():
                if isinstance(version, str) and (version == "*" or version.startswith("dev-")):
                    risk_points += 2
        except Exception:
            warnings.append("Unable to parse composer.json")

        if not (repo_path / "composer.lock").exists():
            warnings.append("No composer.lock detected")
            risk_points += 5

    gradle = repo_path / "build.gradle"
    gradle_kts = repo_path / "build.gradle.kts"
    for gradle_file in (gradle, gradle_kts):
        if gradle_file.exists():
            content = gradle_file.read_text(encoding="utf-8", errors="ignore")
            if "+" in content:
                warnings.append(f"Dynamic versions in {gradle_file.name}")
                risk_points += 3

    dockerfile = repo_path / "Dockerfile"
    if dockerfile.exists():
        for line in dockerfile.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("FROM"):
                if ":" not in stripped or stripped.endswith(":latest"):
                    warnings.append("Dockerfile uses latest or unpinned base image")
                    risk_points += 3

    score = max(0.0, 100.0 - risk_points * 5)
    return score, warnings


def analyze_codebase(repo_path: Path) -> CodebaseReport:
    """Run static analysis over the repository files."""
    report = CodebaseReport()

    for path in repo_path.rglob("*"):
        if path.is_dir():
            if path.name in IGNORED_DIRS:
                continue
            continue

        if any(part in IGNORED_DIRS for part in path.parts):
            continue

        language = _detect_language(path)
        if not language:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        total, code, comments, blanks = _count_lines(content, language)
        report.total_files += 1
        report.total_lines += total
        report.code_lines += code
        report.comment_lines += comments
        report.blank_lines += blanks
        report.language_files[language] = report.language_files.get(language, 0) + 1
        report.language_code_lines[language] = report.language_code_lines.get(language, 0) + code

        report.complexity += _complexity_for_content(content)

        if _is_test_path(path):
            report.test_files += 1

    complexity_per_100 = (report.complexity / max(report.code_lines, 1)) * 100
    if complexity_per_100 <= 10:
        report.complexity_score = 90
    elif complexity_per_100 <= 20:
        report.complexity_score = 70
    elif complexity_per_100 <= 30:
        report.complexity_score = 50
    elif complexity_per_100 <= 40:
        report.complexity_score = 30
    else:
        report.complexity_score = 10

    comment_ratio = report.comment_lines / max(report.code_lines, 1)
    if comment_ratio >= 0.15:
        report.comment_score = 90
    elif comment_ratio >= 0.1:
        report.comment_score = 75
    elif comment_ratio >= 0.05:
        report.comment_score = 60
    else:
        report.comment_score = 40

    test_ratio = report.test_files / max(report.total_files, 1)
    if test_ratio >= 0.2:
        report.test_score = 90
    elif test_ratio >= 0.1:
        report.test_score = 75
    elif test_ratio >= 0.05:
        report.test_score = 60
    else:
        report.test_score = 40

    dependency_score, warnings = _dependency_risk(repo_path)
    report.dependency_score = dependency_score
    report.dependency_warnings = warnings

    report.overall_score = (
        report.complexity_score * 0.35 +
        report.comment_score * 0.2 +
        report.test_score * 0.2 +
        report.dependency_score * 0.25
    )

    return report
