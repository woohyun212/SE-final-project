import secrets
import warnings
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

_INSECURE_DEFAULT_KEY = "your-secret-key-change-in-production"

class Settings(BaseSettings):
    # App
    APP_NAME: str = "LMS API"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./lms.db"

    # JWT
    SECRET_KEY: str = _INSECURE_DEFAULT_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("SECRET_KEY")
    @classmethod
    def warn_insecure_secret(cls, v: str) -> str:
        if v == _INSECURE_DEFAULT_KEY:
            warnings.warn(
                "SECRET_KEY is using the insecure default value. "
                "Set a strong SECRET_KEY environment variable before deploying to production.",
                stacklevel=2,
            )
        return v

    class Config:
        env_file = ".env"

settings = Settings()
