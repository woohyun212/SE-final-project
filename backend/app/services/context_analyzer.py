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

_TIME_KEYWORDS: dict[str, list[str]] = {
    "morning":   ["아침", "새벽", "morning"],
    "afternoon": ["점심", "낮", "오후", "afternoon"],
    "evening":   ["저녁", "evening"],
    "night":     ["밤", "야간", "night"],
}
_LOCATION_KEYWORDS: dict[str, list[str]] = {
    "home":    ["집", "방", "거실", "home"],
    "cafe":    ["카페", "커피숍", "cafe"],
    "gym":     ["헬스장", "헬스", "gym"],
    "office":  ["사무실", "회사", "직장", "office"],
    "commute": ["지하철", "버스", "출퇴근", "commute"],
    "outdoor": ["공원", "야외", "outdoor"],
}
_ACTIVITY_KEYWORDS: dict[str, list[str]] = {
    "exercising": ["운동", "달리", "exercise"],
    "studying":   ["공부", "독서", "study"],
    "working":    ["업무", "회의", "일하", "work"],
    "relaxing":   ["쉬", "휴식", "relax"],
    "commuting":  ["출퇴근", "이동", "commut"],
    "socializing": ["친구", "모임", "friend"],
}
_EMOTION_KEYWORDS: dict[str, list[str]] = {
    "happy":       ["기쁘", "행복", "신나", "좋아", "happy"],
    "sad":         ["슬프", "슬픈", "우울", "눈물", "sad"],
    "angry":       ["화나", "화가", "짜증", "angry"],
    "anxious":     ["불안", "긴장", "걱정", "anxious"],
    "calm":        ["평온", "차분", "편안", "calm"],
    "energetic":   ["활기", "에너지", "힘찬", "energetic"],
    "melancholic": ["쓸쓸", "허전", "그리워", "melancholic"],
}


def _rule_based_context(text: str) -> ContextResult:
    t = text.lower()

    time_of_day = next((k for k, kws in _TIME_KEYWORDS.items() if any(kw in t for kw in kws)), None)
    location = next((k for k, kws in _LOCATION_KEYWORDS.items() if any(kw in t for kw in kws)), None)
    activity = next((k for k, kws in _ACTIVITY_KEYWORDS.items() if any(kw in t for kw in kws)), None)
    emotions = {k: 0.8 for k, kws in _EMOTION_KEYWORDS.items() if any(kw in t for kw in kws)} or None

    return ContextResult(time_of_day=time_of_day, location=location, activity=activity, emotions=emotions)


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

    async def analyze(self, text: str) -> tuple[ContextResult, bool]:
        """LLM으로 맥락 분석. 실패 시 (rule-based 결과, True) 반환."""
        if not text or not text.strip():
            return ContextResult(), False

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
            return ContextResult.model_validate(data), False
        except TimeoutError:
            logger.warning("ContextAnalyzer timed out after %.1fs — rule-based fallback", _ANALYZE_TIMEOUT)
            return _rule_based_context(text), True
        except Exception as exc:
            logger.warning("ContextAnalyzer failed: %s — rule-based fallback", exc)
            return _rule_based_context(text), True


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
