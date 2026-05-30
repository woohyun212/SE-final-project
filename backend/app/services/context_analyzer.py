import asyncio
import json
import logging
import os
import re
from pathlib import Path

from google import genai

from app.schemas.context import ContextResult

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "context-analysis.md"
_ANALYZE_TIMEOUT = float(os.getenv("CONTEXT_ANALYZER_TIMEOUT", "10"))


def _load_prompt_template() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


class ContextAnalyzer:
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=key)
        self._model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self._prompt_template = _load_prompt_template()

    async def analyze(self, text: str) -> ContextResult:
        if not text or not text.strip():
            return ContextResult()

        prompt = self._prompt_template.replace("{text}", text)
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                ),
                timeout=_ANALYZE_TIMEOUT,
            )
            raw = response.text.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
            if match:
                raw = match.group(1)
            data = json.loads(raw)
            return ContextResult.model_validate(data)
        except TimeoutError:
            logger.warning("ContextAnalyzer timed out after %.1fs", _ANALYZE_TIMEOUT)
            return ContextResult()
        except Exception as exc:
            logger.warning("ContextAnalyzer failed: %s", exc)
            return ContextResult()


_analyzer: ContextAnalyzer | None = None


def get_context_analyzer() -> ContextAnalyzer | None:
    global _analyzer
    if _analyzer is not None:
        return _analyzer
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.info("GEMINI_API_KEY not set — ContextAnalyzer disabled")
        return None
    try:
        _analyzer = ContextAnalyzer()
    except Exception as exc:
        logger.error("ContextAnalyzer init failed: %s", exc)
        return None
    return _analyzer
