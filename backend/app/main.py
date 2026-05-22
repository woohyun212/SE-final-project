from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.models import token as _token_models  # noqa: F401 — registers RefreshToken with Base
from app.routers import auth, spotify
from app.services import spotify as spotify_svc


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

app.include_router(auth.router)
app.include_router(spotify.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"message": "Hello World"}
