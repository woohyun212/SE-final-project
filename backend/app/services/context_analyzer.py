import json
import logging
import os
from pathlib import Path

from google import genai
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "context-analysis.md"

_TIME_OF_DAY = {"morning", "afternoon", "evening", "night"}
_LOCATION = {"home", "commute", "gym", "office", "outdoor", "cafe"}
_ACTIVITY = {"working", "exercising", "relaxing", "studying", "commuting", "socializing"}
_EMOTION_LABELS = {"happy", "sad", "angry", "anxious", "calm", "energetic", "melancholic"}


class ContextResult(BaseModel):
    time_of_day: str | None = None
    location: str | None = None
    activity: str | None = None
    emotions: dict | None = None

    @field_validator("time_of_day")
    @classmethod
    def _validate_time(cls, v: str | None) -> str | None:
        if v is not None and v not in _TIME_OF_DAY:
            return None
        return v

    @field_validator("location")
    @classmethod
    def _validate_location(cls, v: str | None) -> str | None:
        if v is not None and v not in _LOCATION:
            return None
        return v

    @field_validator("activity")
    @classmethod
    def _validate_activity(cls, v: str | None) -> str | None:
        if v is not None and v not in _ACTIVITY:
            return None
        return v

    @field_validator("emotions", mode="before")
    @classmethod
    def _validate_emotions(cls, v: dict | None) -> dict[str, float] | None:
        if v is None:
            return None
        cleaned: dict[str, float] = {}
        for k, score in v.items():
            if k not in _EMOTION_LABELS:
                continue
            try:
                f = float(score)
            except (TypeError, ValueError):
                continue
            if 0.0 <= f <= 1.0:
                cleaned[k] = f
        return cleaned or None


def _load_prompt_template() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


class ContextAnalyzer:
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=key)
        self._model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
        self._prompt_template = _load_prompt_template()

    async def analyze(self, text: str) -> ContextResult:
        if not text or not text.strip():
            return ContextResult()

        prompt = self._prompt_template.replace("{text}", text)
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model_name,
                contents=prompt,
            )
            raw = response.text.strip()
            # strip accidental markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            return ContextResult.model_validate(data)
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
    _analyzer = ContextAnalyzer()
    return _analyzer
