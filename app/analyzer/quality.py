"""Code Quality Analysis Module"""

import logging
import asyncio
import random
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.analyzer.git_analyzer import CommitInfo
from app.analyzer.ollama import OllamaClient

import config

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Quality analysis report for a commit"""
    sha: str
    overall_score: float
    commit_message_score: float
    code_complexity_score: float
    documentation_score: float
    test_coverage_score: float
    consistency_score: float
    best_practices_score: float
    summary: str
    analyzed_by_llm: bool = False


class QualityAnalyzer:
    """Analyzes code quality using heuristics and LLM"""

    def __init__(self, ollama_client: OllamaClient = None):
        self.ollama = ollama_client or OllamaClient()
        self._ollama_available = None

    async def check_ollama(self) -> bool:
        """Check if Ollama is available"""
        if self._ollama_available is None:
            self._ollama_available = await self.ollama.is_available()
        return self._ollama_available

    async def analyze_commit(self, commit: CommitInfo, use_llm: bool = True) -> QualityReport:
        """Analyze a single commit's quality"""

        # Start with heuristic analysis
        scores = self._heuristic_analysis(commit)
        analyzed_by_llm = False

        # Optionally enhance with LLM
        if use_llm and await self.check_ollama():
            try:
                llm_scores = await self.ollama.analyze_code_quality(
                    commit.diff_content,
                    commit.message
                )
                # Blend heuristic and LLM scores (60% LLM, 40% heuristic)
                scores = self._blend_scores(scores, llm_scores, llm_weight=0.6)
                analyzed_by_llm = True
            except Exception as e:
                logger.warning(f"LLM analysis failed, using heuristics: {e}")

        return QualityReport(
            sha=commit.sha,
            overall_score=scores.get("overall_score", 50),
            commit_message_score=scores.get("commit_message_score", 50),
            code_complexity_score=scores.get("code_complexity_score", 50),
            documentation_score=scores.get("documentation_score", 50),
            test_coverage_score=scores.get("test_coverage_score", 50),
            consistency_score=scores.get("consistency_score", 50),
            best_practices_score=scores.get("best_practices_score", 50),
            summary=scores.get("summary", ""),
            analyzed_by_llm=analyzed_by_llm
        )

    def _heuristic_analysis(self, commit: CommitInfo) -> Dict[str, float]:
        """Perform heuristic-based quality analysis"""
        scores = {}

        # Commit message analysis
        scores["commit_message_score"] = self._analyze_commit_message(commit.message)

        # Code complexity (based on diff size)
        scores["code_complexity_score"] = self._analyze_complexity(commit)

        # Documentation presence
        scores["documentation_score"] = self._analyze_documentation(commit)

        # Test coverage indicators
        scores["test_coverage_score"] = self._analyze_test_coverage(commit)

        # Consistency
        scores["consistency_score"] = self._analyze_consistency(commit)

        # Best practices
        scores["best_practices_score"] = self._analyze_best_practices(commit)

        # Calculate overall
        weights = config.QUALITY_WEIGHTS
        scores["overall_score"] = sum(
            scores.get(key.replace("_weight", "_score"), 50) * weight
            for key, weight in weights.items()
        )

        scores["summary"] = self._generate_summary(scores)

        return scores

    def _analyze_commit_message(self, message: str) -> float:
        """Analyze commit message quality"""
        score = 50

        if not message:
            return 20

        # Length
        if len(message) < 10:
            score -= 20
        elif len(message) >= 20:
            score += 10

        # Has body
        if '\n\n' in message and len(message.split('\n\n')[1]) > 20:
            score += 15

        # Starts with capital
        if message[0].isupper():
            score += 5

        # Conventional commits
        prefixes = ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore', 'perf', 'ci', 'build']
        if any(message.lower().startswith(f"{p}:") or message.lower().startswith(f"{p}(") for p in prefixes):
            score += 15

        # Has reference
        if '#' in message or any(ref in message.lower() for ref in ['fixes', 'closes', 'resolves']):
            score += 10

        # Negative patterns
        bad_patterns = ['wip', 'temp', 'test123', 'asdf', 'xxx', 'todo', 'fixme']
        if any(bad in message.lower() for bad in bad_patterns):
            score -= 15

        return max(0, min(100, score))

    def _analyze_complexity(self, commit: CommitInfo) -> float:
        """Analyze code complexity (lower complexity = higher score)"""
        total_changes = commit.lines_added + commit.lines_removed

        if total_changes == 0:
            return 70  # No changes, neutral

        # Penalize very large commits
        if total_changes > 1000:
            return 20
        elif total_changes > 500:
            return 40
        elif total_changes > 200:
            return 60
        elif total_changes > 50:
            return 75
        else:
            return 85  # Small, focused commits

    def _analyze_documentation(self, commit: CommitInfo) -> float:
        """Check for documentation in the diff"""
        diff = commit.diff_content.lower()

        if not diff:
            return 50

        score = 50

        # Check for docstrings/comments
        doc_patterns = ['"""', "'''", '//', '/*', '#', 'readme', '.md']
        for pattern in doc_patterns:
            if pattern in diff:
                score += 8

        # Check for documentation files
        doc_files = ['.md', '.rst', '.txt', 'doc', 'readme']
        if any(f in diff.lower() for f in doc_files):
            score += 15

        return min(100, score)

    def _analyze_test_coverage(self, commit: CommitInfo) -> float:
        """Check for test-related changes"""
        diff = commit.diff_content.lower()
        message = commit.message.lower()

        if not diff:
            return 30

        score = 30

        # Test file patterns
        test_patterns = ['test_', '_test.', '.test.', 'spec.', '_spec.', 'tests/', '__tests__']
        for pattern in test_patterns:
            if pattern in diff:
                score += 20
                break

        # Test framework patterns
        test_frameworks = ['pytest', 'unittest', 'jest', 'mocha', 'junit', 'assert', 'expect(']
        for pattern in test_frameworks:
            if pattern in diff:
                score += 10
                break

        # Message mentions tests
        if 'test' in message:
            score += 10

        return min(100, score)

    def _analyze_consistency(self, commit: CommitInfo) -> float:
        """Analyze code consistency (simplified)"""
        diff = commit.diff_content

        if not diff:
            return 60

        score = 60

        # Check for mixed indentation (tabs and spaces)
        lines = diff.split('\n')
        has_tabs = any('\t' in line for line in lines if line.startswith('+'))
        has_spaces = any(line.startswith('+') and '    ' in line for line in lines)

        if has_tabs and has_spaces:
            score -= 15

        # Very long lines
        long_lines = sum(1 for line in lines if line.startswith('+') and len(line) > 120)
        if long_lines > 5:
            score -= 10

        return max(0, min(100, score))

    def _analyze_best_practices(self, commit: CommitInfo) -> float:
        """Check for best practices"""
        diff = commit.diff_content.lower()

        if not diff:
            return 50

        score = 60

        # Negative patterns (security, debugging)
        bad_patterns = [
            'password', 'secret', 'api_key', 'apikey', 'token',  # Potential secrets
            'console.log', 'print(', 'debugger',  # Debug statements
            'todo', 'fixme', 'hack', 'xxx',  # Technical debt
            'eval(', 'exec(',  # Dangerous functions
        ]
        for pattern in bad_patterns:
            if f'+{pattern}' in diff or f'+ {pattern}' in diff:
                score -= 8

        # Positive patterns
        good_patterns = [
            'try:', 'catch', 'except',  # Error handling
            'logger', 'logging',  # Proper logging
            'typing', '-> ', ': str', ': int',  # Type hints
            'async ', 'await ',  # Modern async
        ]
        for pattern in good_patterns:
            if pattern in diff:
                score += 5

        return max(0, min(100, score))

    def _blend_scores(self, heuristic: Dict, llm: Dict, llm_weight: float = 0.6) -> Dict:
        """Blend heuristic and LLM scores"""
        h_weight = 1 - llm_weight
        blended = {}

        for key in heuristic:
            if key == "summary":
                blended[key] = llm.get(key, heuristic[key])
            else:
                h_val = heuristic.get(key, 50)
                l_val = llm.get(key, 50)
                blended[key] = round(h_val * h_weight + l_val * llm_weight, 1)

        return blended

    def _generate_summary(self, scores: Dict) -> str:
        """Generate a brief summary"""
        overall = scores.get("overall_score", 50)

        if overall >= 80:
            return "High quality contribution"
        elif overall >= 60:
            return "Good quality with minor improvements possible"
        elif overall >= 40:
            return "Acceptable quality, consider improvements"
        else:
            return "Quality concerns detected"

    async def analyze_sample(
        self,
        commits: List[CommitInfo],
        sample_size: int = None,
        use_llm: bool = True
    ) -> List[QualityReport]:
        """Analyze a sample of commits"""
        sample_size = sample_size or config.QUALITY_SAMPLE_SIZE

        if len(commits) <= sample_size:
            sample = commits
        else:
            # Stratified sampling - recent + random
            recent = commits[:sample_size // 2]
            older = random.sample(commits[sample_size // 2:], min(sample_size // 2, len(commits) - sample_size // 2))
            sample = recent + older

        reports = []
        for commit in sample:
            report = await self.analyze_commit(commit, use_llm=use_llm)
            reports.append(report)
            # Small delay to avoid overwhelming Ollama
            if use_llm:
                await asyncio.sleep(0.1)

        return reports
