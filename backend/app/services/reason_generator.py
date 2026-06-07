import asyncio
import json
import logging
import os
import re
from pathlib import Path

from google import genai

from app.models.music_catalog import MusicCatalog
from app.schemas.context import ContextResult

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "recommendation-reason.md"
_REASON_TIMEOUT = float(os.getenv("REASON_GENERATOR_TIMEOUT", "15"))
# LLM 호출 1번에 담는 트랙 수를 제한한다 — 출력 토큰(=생성 시간)이 트랙 수에 비례해
# 늘어나 15초 타임아웃을 넘기는 사례가 있었다 (#177). 상위 랭크 트랙만 LLM 이유를
# 받고 나머지는 규칙 기반으로 채워, 응답 지연 위험을 줄이면서 가장 눈에 띄는
# 추천에는 LLM 품질을 유지한다.
_LLM_REASON_LIMIT = int(os.getenv("REASON_GENERATOR_LLM_LIMIT", "5"))


def _rule_based_reason(track: MusicCatalog) -> str:
    parts: list[str] = []
    if track.valence >= 0.7:
        parts.append("밝고 긍정적인 에너지")
    elif track.valence <= 0.3:
        parts.append("감성적이고 잔잔한 무드")
    if track.energy >= 0.7:
        parts.append("활기찬 비트")
    elif track.energy <= 0.3:
        parts.append("차분한 템포")
    if track.acousticness >= 0.7:
        parts.append("어쿠스틱한 감성")
    if track.danceability >= 0.7:
        parts.append("흥겨운 리듬감")
    if track.instrumentalness >= 0.5:
        parts.append("집중하기 좋은 연주")
    if not parts:
        parts.append("현재 감정 상태에 어울리는 분위기")
    return f"{', '.join(parts)}의 곡으로 현재 감정과 잘 어울립니다."


def _load_prompt_template() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


class ReasonGenerator:
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=key)
        self._model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self._prompt_template = _load_prompt_template()

    async def generate(
        self,
        tracks: list[MusicCatalog],
        valence: float,
        arousal: float,
        dominance: float,
        context: ContextResult | None = None,
    ) -> tuple[dict[str, str], bool]:
        """LLM으로 추천 이유 생성. 실패 시 (rule-based 결과, True) 반환.

        트랙이 많을수록 LLM 출력 토큰이 늘어나 타임아웃 위험이 커지므로, 상위
        `_LLM_REASON_LIMIT`개만 LLM에 보내고 나머지는 규칙 기반으로 채운다.
        이 분배는 의도된 동작이라 fallback=True로 표시하지 않는다 — 실제 LLM
        호출이 실패/타임아웃했을 때만 fallback=True를 반환한다.
        """
        if not tracks:
            return {}, False

        llm_tracks = tracks[:_LLM_REASON_LIMIT]
        rule_reasons = {t.track_id: _rule_based_reason(t) for t in tracks[_LLM_REASON_LIMIT:]}

        tracks_data = [
            {
                "track_id": t.track_id,
                "title": t.track_name,
                "artist": t.artists,
                "genre": t.track_genre,
                "valence": round(t.valence, 2),
                "energy": round(t.energy, 2),
                "danceability": round(t.danceability, 2),
                "acousticness": round(t.acousticness, 2),
            }
            for t in llm_tracks
        ]

        context_lines: list[str] = []
        if context:
            if context.time_of_day:
                context_lines.append(f"- Time of day: {context.time_of_day}")
            if context.location:
                context_lines.append(f"- Location: {context.location}")
            if context.activity:
                context_lines.append(f"- Activity: {context.activity}")
            if context.emotions:
                top = max(context.emotions, key=context.emotions.__getitem__)
                context_lines.append(f"- Primary emotion: {top}")

        prompt = (
            self._prompt_template
            .replace("{valence}", str(round(valence, 2)))
            .replace("{arousal}", str(round(arousal, 2)))
            .replace("{dominance}", str(round(dominance, 2)))
            .replace("{context_block}", "\n".join(context_lines) or "- No additional context")
            .replace("{tracks_json}", json.dumps(tracks_data, ensure_ascii=False))
        )

        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                ),
                timeout=_REASON_TIMEOUT,
            )
            raw = response.text.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
            if match:
                raw = match.group(1)
            data = json.loads(raw)
            valid_ids = {t.track_id for t in llm_tracks}
            llm_reasons = {k: str(v) for k, v in data.items() if k in valid_ids}
            for t in llm_tracks:
                llm_reasons.setdefault(t.track_id, _rule_based_reason(t))
            return {**llm_reasons, **rule_reasons}, False
        except TimeoutError:
            logger.warning("ReasonGenerator timed out after %.1fs — rule-based fallback", _REASON_TIMEOUT)
            return {t.track_id: _rule_based_reason(t) for t in tracks}, True
        except Exception as exc:
            logger.warning("ReasonGenerator failed: %s — rule-based fallback", exc)
            return {t.track_id: _rule_based_reason(t) for t in tracks}, True


_generator: ReasonGenerator | None = None


def get_reason_generator() -> ReasonGenerator | None:
    global _generator
    if _generator is not None:
        return _generator
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.info("GEMINI_API_KEY not set — ReasonGenerator disabled")
        return None
    try:
        _generator = ReasonGenerator()
    except Exception as exc:
        logger.error("ReasonGenerator init failed: %s", exc)
        return None
    return _generator
