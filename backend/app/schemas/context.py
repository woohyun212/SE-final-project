from pydantic import BaseModel, field_validator

_TIME_OF_DAY = {"morning", "afternoon", "evening", "night"}
_LOCATION = {"home", "commute", "gym", "office", "outdoor", "cafe"}
_ACTIVITY = {"working", "exercising", "relaxing", "studying", "commuting", "socializing"}
_EMOTION_LABELS = {"happy", "sad", "angry", "anxious", "calm", "energetic", "melancholic"}


class ContextResult(BaseModel):
    time_of_day: str | None = None
    location: str | None = None
    activity: str | None = None
    emotions: dict[str, float] | None = None

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
        if len(cleaned) > 3:
            cleaned = dict(sorted(cleaned.items(), key=lambda x: x[1], reverse=True)[:3])
        return cleaned or None
