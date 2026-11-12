from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

app = FastAPI(
    title="goflow.ai API",
    description="AI video production orchestration backend",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "app": "goflow.ai",
        "status": "online",
        "version": "0.1.0"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/capabilities")
def capabilities():
    return {
        "story_planning": True,
        "storyboard": True,
        "timeline": True,
        "image_generation": "provider_not_connected",
        "video_generation": "provider_not_connected",
        "tamil_voice": "provider_not_connected",
        "ffmpeg_rendering": "not_configured",
        "media_quality_control": "not_configured"
    }
