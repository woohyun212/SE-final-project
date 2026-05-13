from fastapi import FastAPI


app = FastAPI(
    title="Emotion Music Recommendation Backend",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"message": "Hello World"}
