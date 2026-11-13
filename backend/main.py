from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

APP_VERSION = "0.2.0"
DATA_DIR = Path(os.getenv("GOFLOW_DATA_DIR", Path(__file__).parent / "data")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
DB_PATH = DATA_DIR / "goflow.sqlite3"
MAX_UPLOAD_BYTES = int(os.getenv("GOFLOW_MAX_UPLOAD_BYTES", str(500 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}

for directory in (UPLOAD_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def require_api_key(x_goflow_key: str | None = Header(default=None)) -> None:
    configured = os.getenv("GOFLOW_API_KEY")
    if not configured:
        raise HTTPException(503, "Media processing is disabled until GOFLOW_API_KEY is configured.")
    if not x_goflow_key or x_goflow_key != configured:
        raise HTTPException(401, "A valid goflow API key is required for media operations.")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS media (
                id TEXT PRIMARY KEY, filename TEXT NOT NULL, stored_name TEXT NOT NULL,
                size_bytes INTEGER NOT NULL, duration_seconds REAL, width INTEGER,
                height INTEGER, created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, media_id TEXT NOT NULL, status TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0, request_json TEXT NOT NULL,
                output_name TEXT, error TEXT, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(media_id) REFERENCES media(id)
            )
        """)
        db.commit()


init_db()

app = FastAPI(
    title="goflow.ai API",
    description="Video production orchestration API with a persistent local media queue",
    version=APP_VERSION,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("GOFLOW_CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ClipRange(BaseModel):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)


class RenderRequest(BaseModel):
    media_id: str
    start_seconds: float = Field(default=0, ge=0)
    duration_seconds: float | None = Field(default=None, gt=0, le=3600)
    clips: list[ClipRange] = Field(default_factory=list, max_length=100)
    output_width: int = Field(default=1080, ge=320, le=3840)
    output_height: int = Field(default=1920, ge=320, le=3840)
    preset: str = Field(default="balanced", pattern="^(fast|balanced|quality)$")


def get_media(media_id: str) -> dict[str, Any] | None:
    with connect_db() as db:
        row = db.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
    return dict(row) if row else None


def get_job(job_id: str) -> dict[str, Any] | None:
    with connect_db() as db:
        row = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result["request"] = json.loads(result.pop("request_json"))
    return result


def update_job(job_id: str, **values: Any) -> None:
    values["updated_at"] = utc_now()
    assignments = ", ".join(f"{key} = ?" for key in values)
    with connect_db() as db:
        db.execute(
            f"UPDATE jobs SET {assignments} WHERE id = ?",
            (*values.values(), job_id),
        )
        db.commit()


def probe_media(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is not installed on the API/worker host")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height",
         "-of", "json", str(path)],
        capture_output=True, text=True, timeout=60, check=True,
    )
    payload = json.loads(result.stdout)
    video = next((s for s in payload.get("streams", []) if s.get("codec_type") == "video"), {})
    duration = float(payload.get("format", {}).get("duration", 0) or 0)
    return {"duration_seconds": duration, "width": video.get("width"), "height": video.get("height")}


def run_render(job_id: str) -> None:
    job = get_job(job_id)
    if not job:
        return
    media = get_media(job["media_id"])
    if not media:
        update_job(job_id, status="failed", error="Source media record was not found")
        return
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        update_job(job_id, status="failed", error="FFmpeg is not installed on the worker host")
        return

    request = job["request"]
    source = UPLOAD_DIR / media["stored_name"]
    output_name = f"{job_id}.mp4"
    output = OUTPUT_DIR / output_name
    update_job(job_id, status="processing", progress=5, error=None)
    try:
        command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
        command += ["-i", str(source)]
        preset = {"fast": "veryfast", "balanced": "medium", "quality": "slow"}[request["preset"]]
        width, height = request["output_width"], request["output_height"]
        video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )
        clips = request.get("clips") or []
        if clips:
            # Detect audio once so silent source videos remain renderable.
            audio_probe = subprocess.run(
                [shutil.which("ffprobe") or "ffprobe", "-v", "error",
                 "-select_streams", "a", "-show_entries", "stream=index",
                 "-of", "json", str(source)],
                capture_output=True, text=True, timeout=60, check=True,
            )
            has_audio = bool(json.loads(audio_probe.stdout).get("streams"))
            filters = []
            concat_inputs = []
            for index, clip in enumerate(clips):
                start, end = clip["start_seconds"], clip["end_seconds"]
                filters.append(
                    f"[0:v:0]trim=start={start}:end={end},setpts=PTS-STARTPTS,"
                    f"{video_filter}[v{index}]"
                )
                concat_inputs.append(f"[v{index}]")
                if has_audio:
                    filters.append(
                        f"[0:a:0]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{index}]"
                    )
                    concat_inputs.append(f"[a{index}]")
            audio_flag = 1 if has_audio else 0
            filters.append(
                "".join(concat_inputs) +
                f"concat=n={len(clips)}:v=1:a={audio_flag}[vout]" +
                ("[aout]" if has_audio else "")
            )
            command += [
                "-filter_complex", ";".join(filters), "-map", "[vout]",
            ]
            if has_audio:
                command += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
        else:
            if request["start_seconds"] > 0:
                command += ["-ss", str(request["start_seconds"])]
            if request.get("duration_seconds") is not None:
                command += ["-t", str(request["duration_seconds"])]
            command += ["-map", "0:v:0", "-map", "0:a?", "-vf", video_filter]
            command += ["-c:a", "aac", "-b:a", "192k"]
        command += [
            "-c:v", "libx264", "-preset", preset, "-crf", "21",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
        ]
        update_job(job_id, progress=15)
        completed = subprocess.run(command, capture_output=True, text=True, timeout=4 * 60 * 60)
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or "FFmpeg render failed")[-3000:])
        update_job(job_id, status="completed", progress=100, output_name=output_name)
    except Exception as exc:
        output.unlink(missing_ok=True)
        update_job(job_id, status="failed", error=str(exc)[:3000], progress=0)


@app.get("/")
def root():
    return {"app": "goflow.ai", "status": "online", "version": APP_VERSION}


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": utc_now()}


@app.get("/api/v1/capabilities")
def capabilities():
    return {
        "story_planning": True,
        "storyboard": True,
        "timeline": True,
        "media_upload": True,
        "persistent_job_records": True,
        "ffmpeg_rendering": "available" if shutil.which("ffmpeg") else "not_installed",
        "ffprobe": "available" if shutil.which("ffprobe") else "not_installed",
        "transcription": "not_connected",
        "image_generation": "provider_not_connected",
        "video_generation": "provider_not_connected",
        "tamil_voice": "provider_not_connected",
        "media_quality_control": "basic_output_validation_pending",
    }


@app.post("/api/v1/media/upload")
async def upload_media(file: UploadFile = File(...), _authorized: None = Depends(require_api_key)):
    original_name = Path(file.filename or "upload").name
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Unsupported video type. Upload MP4, MOV, MKV, WebM or M4V.")
    media_id = uuid.uuid4().hex
    stored_name = f"{media_id}{extension}"
    destination = UPLOAD_DIR / stored_name
    size = 0
    try:
        with destination.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, f"Upload exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.")
                target.write(chunk)
        if size == 0:
            raise HTTPException(400, "The uploaded file is empty.")
        metadata = {}
        if shutil.which("ffprobe"):
            metadata = probe_media(destination)
        with connect_db() as db:
            db.execute(
                """INSERT INTO media
                (id, filename, stored_name, size_bytes, duration_seconds, width, height, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (media_id, original_name, stored_name, size, metadata.get("duration_seconds"),
                 metadata.get("width"), metadata.get("height"), utc_now()),
            )
            db.commit()
        return {"id": media_id, "filename": original_name, "size_bytes": size, **metadata}
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@app.post("/api/v1/jobs/render", status_code=202)
def create_render_job(request: RenderRequest, background_tasks: BackgroundTasks, _authorized: None = __import__('fastapi').Depends(require_api_key)):
    media = get_media(request.media_id)
    if not media:
        raise HTTPException(404, "Media not found. Upload a source video first.")
    if not (UPLOAD_DIR / media["stored_name"]).is_file():
        raise HTTPException(410, "Source media file is no longer available.")
    if request.clips:
        for index, clip in enumerate(request.clips, start=1):
            if clip.end_seconds <= clip.start_seconds:
                raise HTTPException(422, f"Clip {index}: end_seconds must be greater than start_seconds.")
            if media["duration_seconds"] is not None and clip.end_seconds > media["duration_seconds"] + 0.05:
                raise HTTPException(422, f"Clip {index}: requested range exceeds the source duration.")
    else:
        if request.start_seconds and media["duration_seconds"] is not None:
            if request.start_seconds >= media["duration_seconds"]:
                raise HTTPException(422, "start_seconds must be shorter than the source video.")
        if request.duration_seconds and media["duration_seconds"] is not None:
            if request.start_seconds + request.duration_seconds > media["duration_seconds"] + 0.05:
                raise HTTPException(422, "Requested render range exceeds the source duration.")
    job_id = uuid.uuid4().hex
    now = utc_now()
    with connect_db() as db:
        db.execute(
            """INSERT INTO jobs
            (id, media_id, status, progress, request_json, created_at, updated_at)
            VALUES (?, ?, 'queued', 0, ?, ?, ?)""",
            (job_id, request.media_id, request.model_dump_json(), now, now),
        )
        db.commit()
    background_tasks.add_task(run_render, job_id)
    return {"job_id": job_id, "status": "queued", "status_url": f"/api/v1/jobs/{job_id}"}


@app.get("/api/v1/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.get("output_name"):
        job["output_url"] = f"/api/v1/jobs/{job_id}/output"
    return job


@app.get("/api/v1/jobs/{job_id}/output")
def job_output(job_id: str, _authorized: None = Depends(require_api_key)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job["status"] != "completed" or not job.get("output_name"):
        raise HTTPException(409, "The render is not complete.")
    path = OUTPUT_DIR / job["output_name"]
    if not path.is_file():
        raise HTTPException(410, "Rendered output is no longer available.")
    return FileResponse(path, media_type="video/mp4", filename=f"goflow-{job_id[:8]}.mp4")
