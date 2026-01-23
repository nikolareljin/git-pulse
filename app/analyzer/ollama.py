"""Ollama LLM Client for Code Quality Analysis"""

import logging
import asyncio
from typing import Optional, Dict, Any
import httpx

import config

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API"""

    def __init__(
        self,
        host: str = None,
        model: str = None,
        timeout: int = None
    ):
        self.host = host or config.OLLAMA_HOST
        self.model = model or config.OLLAMA_MODEL
        self.timeout = timeout or config.OLLAMA_TIMEOUT
        self._available = None

    async def is_available(self) -> bool:
        """Check if Ollama is available"""
        if self._available is not None:
            return self._available

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.host}/api/tags")
                self._available = response.status_code == 200
                if self._available:
                    logger.info(f"Ollama is available at {self.host}")
                return self._available
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            self._available = False
            return False

    async def generate(self, prompt: str, system: str = None) -> Optional[str]:
        """Generate a response from Ollama"""
        if not await self.is_available():
            return None

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
            if system:
                payload["system"] = system

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.host}/api/generate",
                    json=payload
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "")
                else:
                    logger.error(f"Ollama error: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return None

    async def analyze_code_quality(
        self,
        diff_content: str,
        commit_message: str,
        file_types: list = None
    ) -> Dict[str, Any]:
        """Analyze code quality using LLM"""

        if not diff_content or len(diff_content) < 10:
            return self._default_quality_scores()

        system_prompt = """You are a code quality analyzer. Analyze the given code diff and provide quality scores.
You must respond with ONLY a JSON object, no other text. Use this exact format:
{
    "commit_message_score": <0-100>,
    "code_complexity_score": <0-100>,
    "documentation_score": <0-100>,
    "test_coverage_score": <0-100>,
    "consistency_score": <0-100>,
    "best_practices_score": <0-100>,
    "overall_score": <0-100>,
    "summary": "<brief one-line summary>"
}

Scoring guidelines:
- commit_message_score: Clear, descriptive, follows conventions (50=average)
- code_complexity_score: Lower complexity is better (100=simple, 0=very complex)
- documentation_score: Presence of comments, docstrings (50=adequate)
- test_coverage_score: Presence of tests in diff (0 if no tests visible)
- consistency_score: Follows existing code style (50=average)
- best_practices_score: Security, error handling, patterns (50=average)
- overall_score: Weighted average of above"""

        prompt = f"""Analyze this code change:

COMMIT MESSAGE:
{commit_message[:500]}

CODE DIFF (truncated):
{diff_content[:3000]}

Respond with ONLY the JSON object."""

        try:
            response = await self.generate(prompt, system_prompt)
            if response:
                # Try to parse JSON from response
                import json
                # Find JSON in response
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = response[start:end]
                    scores = json.loads(json_str)
                    return self._validate_scores(scores)
        except Exception as e:
            logger.warning(f"Error parsing quality analysis: {e}")

        return self._default_quality_scores()

    def _default_quality_scores(self) -> Dict[str, Any]:
        """Return default quality scores when analysis fails"""
        return {
            "commit_message_score": 50,
            "code_complexity_score": 50,
            "documentation_score": 50,
            "test_coverage_score": 50,
            "consistency_score": 50,
            "best_practices_score": 50,
            "overall_score": 50,
            "summary": "Analysis unavailable"
        }

    def _validate_scores(self, scores: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize scores"""
        default = self._default_quality_scores()

        for key in default:
            if key not in scores:
                scores[key] = default[key]
            elif key != "summary":
                # Ensure numeric scores are in range
                try:
                    scores[key] = max(0, min(100, int(scores[key])))
                except (ValueError, TypeError):
                    scores[key] = default[key]

        return scores

    async def analyze_commit_message(self, message: str) -> int:
        """Quick analysis of commit message quality"""
        # Heuristic scoring without LLM
        score = 50

        # Length checks
        if len(message) < 10:
            score -= 20
        elif len(message) > 50:
            score += 10

        # Has body (multi-line)
        if '\n\n' in message:
            score += 15

        # Starts with capital
        if message and message[0].isupper():
            score += 5

        # Contains ticket reference
        if any(pattern in message.lower() for pattern in ['#', 'fixes', 'closes', 'resolves']):
            score += 10

        # Avoid "WIP", "temp", etc.
        if any(bad in message.lower() for bad in ['wip', 'temp', 'test', 'asdf', 'xxx']):
            score -= 15

        # Conventional commit format
        if any(message.lower().startswith(prefix) for prefix in ['feat:', 'fix:', 'docs:', 'refactor:', 'test:', 'chore:']):
            score += 15

        return max(0, min(100, score))
