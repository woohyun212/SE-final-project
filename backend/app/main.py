from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.models import token as _token_models  # noqa: F401 — registers RefreshToken with Base
from app.routers import auth, spotify


@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


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
