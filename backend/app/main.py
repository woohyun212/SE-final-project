import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models import token as _token_models  # noqa: F401 — registers RefreshToken with Base
from app.routers import auth, spotify
from app.services import spotify as spotify_svc


# Dev defaults: Next.js dev server on both common loopback hosts.
_DEFAULT_CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


def _parse_cors_origins() -> list[str]:
    """Parse ``CORS_ALLOWED_ORIGINS`` (comma-separated) or fall back to dev defaults."""
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins or _DEFAULT_CORS_ORIGINS


@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    await spotify_svc.init_http_client()
    yield
    await spotify_svc.close_http_client()


app = FastAPI(
    title="Emotion Music Recommendation Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(spotify.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"message": "Hello World"}
