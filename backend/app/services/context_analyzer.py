import json
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_FEATURE_KEYS = ("valence", "energy", "danceability", "acousticness", "instrumentalness")
_FEATURE_DEFAULTS: dict[str, float] = {k: 0.5 for k in _FEATURE_KEYS}

_SYSTEM_PROMPT = """\
You are an emotion-to-music feature analyzer.
Given text describing a person's mood, feelings, or situation (Korean or any language),
return a JSON object with these five audio feature values, each a float between 0.0 and 1.0:

- valence: positivity (0=very sad/negative, 1=very happy/positive)
- energy: energy level (0=calm/tired, 1=excited/energetic)
- danceability: how dance-worthy (0=not danceable, 1=very danceable)
- acousticness: preference for acoustic/soft music (0=electronic, 1=acoustic/mellow)
- instrumentalness: preference for instrumental (0=prefer vocals, 1=prefer no vocals)

Respond with only the JSON object, no explanation.\
"""


class ContextAnalyzer:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

    async def analyze(self, text: str) -> dict[str, float]:
        if not text.strip():
            return dict(_FEATURE_DEFAULTS)

        client = genai.Client(api_key=self._api_key)
        response = await client.aio.models.generate_content(
            model=self._model_name,
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=128,
            ),
        )

        raw = (response.text or "").strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("ContextAnalyzer: invalid JSON from model: %.120s", raw)
            return dict(_FEATURE_DEFAULTS)

        result = {
            k: float(max(0.0, min(1.0, parsed.get(k, _FEATURE_DEFAULTS[k]))))
            for k in _FEATURE_KEYS
        }
        logger.info("ContextAnalyzer result: %s", result)
        return result


_analyzer: ContextAnalyzer | None = None


def get_context_analyzer() -> ContextAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = ContextAnalyzer()
    return _analyzer
