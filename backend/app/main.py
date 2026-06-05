import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401 — registers models with SQLAlchemy metadata
from app.routers import auth, feedback, history, recommend

logger = logging.getLogger("app.timing")


# Dev defaults: Next.js dev server on both common loopback hosts.
_DEFAULT_CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins or _DEFAULT_CORS_ORIGINS


app = FastAPI(
    title="Emotion Music Recommendation Backend",
    version="0.1.0",
)


@app.middleware("http")
async def log_response_time(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        # 여기서 잡아야 CORSMiddleware(outer)를 통과해 CORS 헤더가 붙음.
        # @app.exception_handler(Exception)은 ServerErrorMiddleware에 등록되어 CORSMiddleware 바깥에서 동작함.
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s %.1fms", request.method, request.url.path, elapsed_ms)
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
    return response


# CORSMiddleware는 log_response_time(BaseHTTPMiddleware) 이후에 등록해야 outer에 위치함.
# 순서가 바뀌면 500 응답이 CORSMiddleware를 통과하지 못해 CORS 헤더가 누락됨.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(feedback.router)
app.include_router(history.router)
app.include_router(recommend.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"message": "Hello World"}
