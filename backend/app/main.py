import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

import app.models  # noqa: F401 — registers models with SQLAlchemy metadata
from app.routers import auth, recommend

logger = logging.getLogger("app.timing")


@asynccontextmanager
async def lifespan(application: FastAPI):
    yield


app = FastAPI(
    title="Emotion Music Recommendation Backend",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_response_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s %.1fms", request.method, request.url.path, elapsed_ms)
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
    return response


app.include_router(auth.router)
app.include_router(recommend.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"message": "Hello World"}
