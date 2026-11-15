"""Authenticated Studio orchestration routes for goflow.ai.

The default generation adapter is deliberately offline/mock: it never claims to
create media and never makes a billable network request.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from generation_providers import GenerationRequest, submit_generation
from comfyui_client import ComfyUIError, download_output as comfy_download_output, get_history as comfy_history, get_queue as comfy_queue, submit_prompt as comfy_submit, upload_image as comfy_upload_image, upload_video as comfy_upload_video, inspect_wan_animate_readiness
from story_engine import StoryPlanRequest, create_story_plan as build_story_plan
from workflow_catalog import list_workflows
from workflow_registry import WorkflowRegistryError, build_workflow_prompt, get_workflow_form, list_local_workflows
from studio_composer import compose_video
from local_tts import available_engines as local_tts_engines, synthesize_speech
from reference_video import ReferenceVideoError, inspect_reference_video
from reference_analysis import ReferenceAnalysisError, analyze_reference_video

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path() -> Path:
    return Path(os.getenv("GOFLOW_DATA_DIR", Path(__file__).parent / "data")).resolve() / "goflow.sqlite3"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path(), timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def init_studio_db() -> None:
    _db_path().parent.mkdir(parents=True, exist_ok=True)
    with _connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS studio_generations (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL, scene_id TEXT NOT NULL,
                media_type TEXT NOT NULL, provider TEXT NOT NULL, status TEXT NOT NULL,
                request_json TEXT NOT NULL, result_json TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS studio_media (
                id TEXT PRIMARY KEY, filename TEXT NOT NULL, stored_name TEXT NOT NULL,
                media_type TEXT NOT NULL, content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL, source_prompt_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("CREATE TABLE IF NOT EXISTS studio_reference_shot_maps (id TEXT PRIMARY KEY, reference_media_id TEXT NOT NULL, map_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS studio_renders (id TEXT PRIMARY KEY, status TEXT NOT NULL, progress INTEGER NOT NULL, request_json TEXT NOT NULL, output_name TEXT, result_json TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        db.commit()


class GenerationSubmission(BaseModel):
    media_type: Literal["image", "video"]
    request: GenerationRequest


@router.post("/story/plan")
def create_story_plan(request: StoryPlanRequest):
    """Generate an editable offline-first story and storyboard plan."""
    return build_story_plan(request)


@router.post("/generations", status_code=202)
def create_generation(payload: GenerationSubmission):
    try:
        result = submit_generation(payload.media_type, payload.request)
    except (RuntimeError, ValueError, NotImplementedError) as exc:
        raise HTTPException(503, str(exc)) from exc

    init_studio_db()
    now = _now()
    record_id = result.generation_id
    with _connect() as db:
        db.execute(
            """INSERT INTO studio_generations
            (id, project_id, scene_id, media_type, provider, status,
             request_json, result_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record_id, payload.request.project_id, payload.request.scene_id,
             payload.media_type, result.provider, result.status,
             payload.request.model_dump_json(), result.model_dump_json(), now, now),
        )
        db.commit()
    return {"generation_id": record_id, **result.model_dump()}


@router.get("/generations/{generation_id}")
def get_generation(generation_id: str):
    init_studio_db()
    with _connect() as db:
        row = db.execute(
            "SELECT * FROM studio_generations WHERE id = ?", (generation_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Generation record not found.")
    record = dict(row)
    record["request"] = json.loads(record.pop("request_json"))
    record["result"] = json.loads(record.pop("result_json"))
    return record


@router.get("/studio/workflows")
def studio_workflows(category: Literal["image", "video", "audio"] | None = None):
    """List curated templates plus validated locally installed workflows."""
    catalogue = list_workflows(category)
    local = list_local_workflows(category)
    catalogue["local_workflows"] = local
    catalogue["local_count"] = len(local)
    return catalogue


@router.get("/studio/workflows/{workflow_id}")
def studio_workflow_form(workflow_id: str):
    """Return a validated local manifest as a dynamic Creator Studio form."""
    try:
        return get_workflow_form(workflow_id)
    except WorkflowRegistryError as exc:
        raise HTTPException(404, str(exc)) from exc


class LocalWorkflowRun(BaseModel):
    values: dict = Field(default_factory=dict)
    client_id: str | None = Field(default=None, max_length=128)


@router.post("/studio/workflows/{workflow_id}/run", status_code=202)
def run_local_workflow(workflow_id: str, payload: LocalWorkflowRun):
    """Build a graph from a trusted local manifest and submit it to local ComfyUI."""
    try:
        graph, manifest = build_workflow_prompt(workflow_id, payload.values)
    except WorkflowRegistryError as exc:
        raise HTTPException(422, str(exc)) from exc
    try:
        result = comfy_submit(graph, payload.client_id)
    except (ComfyUIError, ValueError) as exc:
        raise HTTPException(503 if isinstance(exc, ComfyUIError) else 422, str(exc)) from exc
    return {
        "provider": "comfyui",
        "workflow_id": workflow_id,
        "workflow_name": manifest.get("name", workflow_id),
        "prompt_id": result["prompt_id"],
        "status": "queued",
        "status_url": f"/api/v1/studio/comfy/jobs/{result['prompt_id']}",
        "estimated_cost": "₹0 from goflow.ai; local hardware only (worker electricity/network costs may apply)",
    }


@router.get("/studio/providers")
def studio_providers():
    return {
        "budget_mode": "zero_cost",
        "default_provider": os.getenv("GOFLOW_GENERATION_PROVIDER", "mock"),
        "image": {"available": False, "mode": "mock", "creates_media": False},
        "video": {"available": False, "mode": "mock", "creates_media": False},
        "voice": {
            "available": any(item["ready"] for item in local_tts_engines().values()),
            "engines": local_tts_engines(),
            "note": "Voice generation runs locally. Piper needs a configured local model; eSpeak needs its Tamil voice installed.",
        },
        "youtube": {
            "available": False,
            "configured": bool(os.getenv("GOFLOW_YOUTUBE_CLIENT_SECRET_FILE")),
            "note": "OAuth credentials and channel authorization are required before publishing.",
        },
    }


def _which(command: str) -> str | None:
    import shutil
    return shutil.which(command)


init_studio_db()


class LocalVoiceoverRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    engine: Literal["auto", "piper", "espeak"] = "auto"
    voice: str = Field(default="ta", min_length=1, max_length=80)
    speed: int = Field(default=145, ge=80, le=250)


@router.post("/studio/voiceovers", status_code=201)
def create_local_voiceover(payload: LocalVoiceoverRequest):
    """Synthesize narration to a local WAV file and register it in Studio media."""
    init_studio_db()
    media_id = uuid.uuid4().hex
    filename = f"voiceover-{media_id[:8]}.wav"
    stored_name = media_id + ".wav"
    destination = _studio_output_dir() / stored_name
    try:
        result = synthesize_speech(
            payload.text, destination, engine=payload.engine,
            voice=payload.voice, speed=payload.speed,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    now = _now()
    try:
        with _connect() as db:
            db.execute(
                """INSERT INTO studio_media
                (id, filename, stored_name, media_type, content_type, size_bytes, source_prompt_id, created_at)
                VALUES (?, ?, ?, 'audio', 'audio/wav', ?, 'local-tts', ?)""",
                (media_id, filename, stored_name, result["size_bytes"], now),
            )
            db.commit()
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {
        "media_id": media_id,
        "filename": filename,
        "media_type": "audio",
        "url": f"/api/v1/studio/media/{media_id}",
        **result,
    }


class ComfyWorkflowSubmission(BaseModel):
    workflow: dict = Field(min_length=1, max_length=1000)
    client_id: str | None = Field(default=None, max_length=128)


@router.post("/studio/comfy/upload-image")
async def upload_comfy_reference_image(file: UploadFile = File(...)):
    """Upload a reference image to the configured local ComfyUI input folder."""
    content_type = (file.content_type or "").lower()
    if content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(415, "Only PNG, JPEG, and WebP reference images are supported.")
    data = await file.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "Reference image exceeds the 20 MB limit.")
    try:
        uploaded = comfy_upload_image(file.filename or "reference-image", content_type, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ComfyUIError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"provider": "comfyui", **uploaded}



@router.post("/studio/comfy/upload-video")
async def upload_comfy_reference_video(file: UploadFile = File(...)):
    """Upload an owned reference video to local ComfyUI input storage."""
    content_type = (file.content_type or "").lower()
    if content_type not in {"video/mp4", "video/webm", "video/quicktime"}:
        raise HTTPException(415, "Only MP4, WebM, and QuickTime reference videos are supported.")
    data = await file.read(100 * 1024 * 1024 + 1)
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(413, "Reference video exceeds the 100 MB limit.")
    try:
        uploaded = comfy_upload_video(file.filename or "reference-video.mp4", content_type, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ComfyUIError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"provider": "comfyui", **uploaded}


@router.post("/studio/reference-videos/{media_id}/shot-map", status_code=201)
def save_reference_shot_map(media_id: str, payload: ReferenceShotMapRequest):
    """Persist an editable shot-by-shot recreation plan for an inspected video."""
    if not re.fullmatch(r"[a-f0-9]{32}", media_id):
        raise HTTPException(422, "Invalid reference media id.")
    init_studio_db()
    with _connect() as db:
        reference = db.execute("SELECT * FROM studio_media WHERE id = ? AND media_type = 'video'", (media_id,)).fetchone()
        if not reference:
            raise HTTPException(404, "Reference video not found.")
        analysis_root = (_studio_output_dir() / "reference-analysis").resolve()
        for shot in payload.shots:
            frame_path = analysis_root / shot.frame_filename
            if not frame_path.is_file() or analysis_root not in frame_path.resolve().parents:
                raise HTTPException(422, f"Reference frame {shot.frame_filename} does not exist.")
            if shot.character_media_id:
                character = db.execute("SELECT media_type FROM studio_media WHERE id = ?", (shot.character_media_id,)).fetchone()
                if not character or character["media_type"] != "image":
                    raise HTTPException(422, "Character media must reference an imported Studio image.")
        now = _now()
        map_id = uuid.uuid4().hex
        map_data = {"map_id": map_id, "reference_media_id": media_id,
                    "shots": [shot.model_dump() for shot in payload.shots]}
        db.execute(
            "INSERT INTO studio_reference_shot_maps (id, reference_media_id, map_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (map_id, media_id, json.dumps(map_data), now, now),
        )
        db.commit()
    return map_data


@router.get("/studio/reference-videos/shot-maps/{map_id}")
def get_reference_shot_map(map_id: str):
    if not re.fullmatch(r"[a-f0-9]{32}", map_id):
        raise HTTPException(422, "Invalid shot map id.")
    init_studio_db()
    with _connect() as db:
        row = db.execute("SELECT map_json FROM studio_reference_shot_maps WHERE id = ?", (map_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Reference shot map not found.")
    return json.loads(row["map_json"])


class ReferenceShot(BaseModel):
    frame_filename: str = Field(pattern=r"^frame-[0-9]{2}\\.jpg$")
    timestamp_seconds: float = Field(ge=0, le=180)
    title: str = Field(default="Shot", min_length=1, max_length=120)
    duration_seconds: float = Field(default=3, gt=0, le=60)
    camera_direction: str = Field(default="Static", max_length=160)
    visual_notes: str = Field(default="", max_length=1000)
    generation_prompt: str = Field(default="", max_length=2000)
    character_media_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


class ReferenceShotMapRequest(BaseModel):
    shots: list[ReferenceShot] = Field(min_length=1, max_length=12)


@router.post("/studio/reference-videos/{media_id}/analyze")
def analyze_stored_reference_video(media_id: str):
    """Extract representative frames and detect candidate scene cuts locally."""
    if not re.fullmatch(r"[a-f0-9]{32}", media_id):
        raise HTTPException(422, "Invalid media id.")
    init_studio_db()
    with _connect() as db:
        row = db.execute("SELECT * FROM studio_media WHERE id = ?", (media_id,)).fetchone()
    if not row or row["media_type"] != "video":
        raise HTTPException(404, "Reference video not found.")
    source = _studio_output_dir() / row["stored_name"]
    if not source.is_file():
        raise HTTPException(410, "Reference video file is no longer available.")
    analysis_id = uuid.uuid4().hex
    frame_dir = _studio_output_dir() / "reference-analysis" / analysis_id
    try:
        result = analyze_reference_video(source, frame_dir, max_frames=12)
    except ReferenceAnalysisError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {
        "analysis_id": analysis_id,
        "reference_media_id": media_id,
        **result,
        "frames": [
            {**frame, "url": f"/api/v1/studio/reference-videos/analysis/{analysis_id}/{frame['filename']}"}
            for frame in result["frames"]
        ],
    }


@router.get("/studio/reference-videos/analysis/{analysis_id}/{filename}")
def get_reference_analysis_frame(analysis_id: str, filename: str):
    if not re.fullmatch(r"[a-f0-9]{32}", analysis_id) or not re.fullmatch(r"frame-[0-9]{2}\.jpg", filename):
        raise HTTPException(422, "Invalid analysis frame path.")
    path = (_studio_output_dir() / "reference-analysis" / analysis_id / filename).resolve()
    root = (_studio_output_dir() / "reference-analysis").resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(404, "Reference analysis frame not found.")
    return FileResponse(path, media_type="image/jpeg", filename=filename)


@router.post("/studio/reference-videos/inspect", status_code=201)
async def inspect_uploaded_reference_video(file: UploadFile = File(...)):
    """Store a reference video locally and return ffprobe metadata for shot planning."""
    content_type = (file.content_type or "").lower()
    allowed_types = {"video/mp4": ".mp4", "video/webm": ".webm",
                     "video/quicktime": ".mov", "video/x-matroska": ".mkv"}
    if content_type not in allowed_types:
        raise HTTPException(415, "Upload an MP4, WebM, QuickTime MOV or Matroska video.")
    data = await file.read(100 * 1024 * 1024 + 1)
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(413, "Reference video exceeds the 100 MB limit.")
    try:
        metadata = inspect_reference_video(data)
    except ReferenceVideoError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    init_studio_db()
    media_id = uuid.uuid4().hex
    filename = Path(file.filename or ("reference" + allowed_types[content_type])).name
    extension = allowed_types[content_type]
    stored_name = media_id + extension
    destination = _studio_output_dir() / stored_name
    destination.write_bytes(data)
    try:
        with _connect() as db:
            db.execute(
                """INSERT INTO studio_media
                (id, filename, stored_name, media_type, content_type, size_bytes, source_prompt_id, created_at)
                VALUES (?, ?, ?, 'video', ?, ?, '', ?)""",
                (media_id, filename, stored_name, content_type, len(data), _now()),
            )
            db.commit()
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {"media_id": media_id, "filename": filename,
            "url": f"/api/v1/studio/media/{media_id}",
            "analysis_status": "metadata_ready", **metadata}


@router.get("/studio/comfy/wan-animate-readiness")
def wan_animate_readiness():
    """Check local Wan Animate nodes and hardware visibility; never downloads models."""
    try:
        return inspect_wan_animate_readiness()
    except ComfyUIError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/studio/comfy/status")
def comfy_status():
    try:
        return {"available": True, "queue": comfy_queue()}
    except ComfyUIError as exc:
        return {"available": False, "error": str(exc)}


@router.post("/studio/comfy/submit", status_code=202)
def submit_comfy_workflow(payload: ComfyWorkflowSubmission):
    try:
        result = comfy_submit(payload.workflow, payload.client_id)
    except (ComfyUIError, ValueError) as exc:
        raise HTTPException(503 if isinstance(exc, ComfyUIError) else 422, str(exc)) from exc
    return {"provider": "comfyui", "prompt_id": result["prompt_id"], "status": "queued",
            "status_url": f"/api/v1/studio/comfy/jobs/{result['prompt_id']}",
            "estimated_cost": "₹0 from goflow.ai; local hardware only (worker electricity/network costs may apply)"}


def _studio_output_dir() -> Path:
    path = Path(os.getenv("GOFLOW_DATA_DIR", Path(__file__).parent / "data")).resolve() / "studio_outputs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _import_comfy_outputs(prompt_id: str, outputs: dict) -> list[dict]:
    # Job history can be queried before any Studio generation has initialized its tables.
    # Ensure the media index exists before idempotency lookups or inserts.
    init_studio_db()
    allowed = {
        ".png": ("image", "image/png"), ".jpg": ("image", "image/jpeg"),
        ".jpeg": ("image", "image/jpeg"), ".webp": ("image", "image/webp"),
        ".mp4": ("video", "video/mp4"), ".webm": ("video", "video/webm"),
        ".gif": ("image", "image/gif"), ".wav": ("audio", "audio/wav"),
        ".mp3": ("audio", "audio/mpeg"),
    }
    imported = []
    for node_outputs in outputs.values():
        if not isinstance(node_outputs, dict):
            continue
        for group in ("images", "gifs", "videos", "audio"):
            items = node_outputs.get(group, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                filename = item.get("filename")
                extension = Path(filename).suffix.lower() if isinstance(filename, str) else ""
                if extension not in allowed:
                    continue
                media_type, expected_type = allowed[extension]
                with _connect() as db:
                    existing = db.execute(
                        "SELECT id, size_bytes FROM studio_media WHERE source_prompt_id = ? AND filename = ?",
                        (prompt_id, filename),
                    ).fetchone()
                if existing:
                    imported.append({
                        "media_id": existing["id"], "filename": filename, "media_type": media_type,
                        "size_bytes": existing["size_bytes"], "url": f"/api/v1/studio/media/{existing['id']}",
                    })
                    continue
                subfolder = item.get("subfolder", "")
                output_type = item.get("type", "output")
                data, content_type = comfy_download_output(filename, subfolder, output_type)
                if not data or len(data) > 500 * 1024 * 1024:
                    raise ComfyUIError("ComfyUI returned an empty or oversized output.")
                # Do not trust an upstream content-type header over the known file extension.
                media_id = uuid.uuid4().hex
                stored_name = media_id + extension
                destination = _studio_output_dir() / stored_name
                destination.write_bytes(data)
                now = _now()
                try:
                    with _connect() as db:
                        db.execute(
                            """INSERT INTO studio_media
                            (id, filename, stored_name, media_type, content_type, size_bytes, source_prompt_id, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (media_id, filename, stored_name, media_type, expected_type, len(data), prompt_id, now),
                        )
                        db.commit()
                except Exception:
                    destination.unlink(missing_ok=True)
                    raise
                imported.append({
                    "media_id": media_id, "filename": filename, "media_type": media_type,
                    "size_bytes": len(data), "url": f"/api/v1/studio/media/{media_id}",
                })
    return imported


@router.get("/studio/media")
def list_studio_media():
    """List locally imported generated assets for the Studio timeline."""
    init_studio_db()
    with _connect() as db:
        rows = db.execute(
            """SELECT id, filename, media_type, content_type, size_bytes,
                      source_prompt_id, created_at
               FROM studio_media ORDER BY created_at DESC LIMIT 200"""
        ).fetchall()
    return {"items": [
        {**dict(row), "url": f"/api/v1/studio/media/{row['id']}"}
        for row in rows
    ]}


@router.get("/studio/media/{media_id}")
def get_studio_media(media_id: str):
    if not re.fullmatch(r"[a-f0-9]{32}", media_id):
        raise HTTPException(422, "Invalid media id.")
    init_studio_db()
    with _connect() as db:
        row = db.execute("SELECT * FROM studio_media WHERE id = ?", (media_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Generated media not found.")
    path = _studio_output_dir() / row["stored_name"]
    if not path.is_file():
        raise HTTPException(410, "Generated media file is no longer available.")
    return FileResponse(path, media_type=row["content_type"], filename=row["filename"])


class CompositionClip(BaseModel):
    media_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    duration: float = Field(gt=0, le=600)
    source_in: float = Field(default=0, ge=0)
    source_out: float | None = Field(default=None, gt=0)
    motion: Literal["static", "zoom_in", "zoom_out", "pan_left", "pan_right"] = "zoom_in"


class AudioTrack(BaseModel):
    media_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    start_seconds: float = Field(default=0, ge=0, le=3600)
    volume: float = Field(default=1.0, ge=0, le=2)
    loop: bool = False


class StudioCompositionRequest(BaseModel):
    clips: list[CompositionClip] = Field(min_length=1, max_length=100)
    audio_media_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    audio_tracks: list[AudioTrack] = Field(default_factory=list, max_length=20)
    width: int = Field(default=1080, ge=320, le=3840)
    height: int = Field(default=1920, ge=320, le=3840)
    preset: Literal["veryfast", "medium", "slow", "veryslow"] = "slow"
    crf: int = Field(default=18, ge=16, le=28)


def _render_output_dir() -> Path:
    path = Path(os.getenv("GOFLOW_DATA_DIR", Path(__file__).parent / "data")).resolve() / "studio_renders"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _studio_media_record(media_id: str) -> dict:
    with _connect() as db:
        row = db.execute("SELECT * FROM studio_media WHERE id = ?", (media_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Studio media was not found.")
    root = _studio_output_dir().resolve()
    path = (root / row["stored_name"]).resolve()
    if not path.is_file() or path.parent != root:
        raise HTTPException(410, "Studio media file is unavailable.")
    return {**dict(row), "path": path}


def _run_studio_composition(render_id: str, payload: dict) -> None:
    output_name = render_id + ".mp4"
    output_path = _render_output_dir() / output_name
    try:
        resolved = []
        for clip in payload["clips"]:
            asset = _studio_media_record(clip["media_id"])
            if asset["media_type"] not in {"image", "video"}:
                raise ValueError("Only image and video assets can be placed on the timeline.")
            resolved.append({"path": asset["path"], "media_type": asset["media_type"],
                             "duration": clip["duration"], "source_in": clip["source_in"],
                             "source_out": clip.get("source_out"), "motion": clip.get("motion", "zoom_in")})
        audio_path = None
        if payload.get("audio_media_id"):
            audio = _studio_media_record(payload["audio_media_id"])
            if audio["media_type"] != "audio":
                raise ValueError("The optional soundtrack must be an audio asset.")
            audio_path = audio["path"]
        audio_tracks = []
        for track in payload.get("audio_tracks", []):
            asset = _studio_media_record(track["media_id"])
            if asset["media_type"] != "audio":
                raise ValueError("Every audio track must reference an audio asset.")
            audio_tracks.append({"path": asset["path"], "start_seconds": track["start_seconds"],
                                 "volume": track["volume"], "loop": track["loop"]})
        with _connect() as db:
            db.execute("UPDATE studio_renders SET status='processing', progress=10, updated_at=? WHERE id=?", (_now(), render_id))
            db.commit()
        result = compose_video(resolved, audio_path, output_path, width=payload["width"], height=payload["height"],
                               preset=payload["preset"], crf=payload["crf"], audio_tracks=audio_tracks)
        with _connect() as db:
            db.execute("UPDATE studio_renders SET status='completed', progress=100, output_name=?, result_json=?, updated_at=? WHERE id=?",
                       (output_name, json.dumps(result), _now(), render_id))
            db.commit()
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        with _connect() as db:
            db.execute("UPDATE studio_renders SET status='failed', progress=0, error=?, updated_at=? WHERE id=?",
                       (str(exc)[:3000], _now(), render_id))
            db.commit()


@router.post("/studio/renders", status_code=202)
def create_studio_render(payload: StudioCompositionRequest):
    init_studio_db()
    clip_rows = [clip.model_dump() for clip in payload.clips]
    for clip in clip_rows:
        asset = _studio_media_record(clip["media_id"])
        if asset["media_type"] not in {"image", "video"}:
            raise HTTPException(422, "Timeline clips must reference image or video assets.")
        if clip.get("source_out") is not None and clip["source_out"] <= clip["source_in"]:
            raise HTTPException(422, "Video source-out must be greater than source-in.")
    if payload.audio_media_id:
        audio = _studio_media_record(payload.audio_media_id)
        if audio["media_type"] != "audio":
            raise HTTPException(422, "audio_media_id must reference an audio asset.")
    for track in payload.audio_tracks:
        audio = _studio_media_record(track.media_id)
        if audio["media_type"] != "audio":
            raise HTTPException(422, "Every audio_tracks.media_id must reference an audio asset.")
    render_id = uuid.uuid4().hex
    now = _now()
    request_data = payload.model_dump()
    with _connect() as db:
        db.execute("INSERT INTO studio_renders (id,status,progress,request_json,created_at,updated_at) VALUES (?, 'queued',0,?,?,?)",
                   (render_id, json.dumps(request_data), now, now))
        db.commit()
    threading.Thread(target=_run_studio_composition, args=(render_id, request_data),
                     name="goflow-studio-render-" + render_id[:8], daemon=True).start()
    return {"render_id": render_id, "status": "queued", "status_url": "/api/v1/studio/renders/" + render_id}


@router.get("/studio/renders/{render_id}")
def studio_render_status(render_id: str):
    if not re.fullmatch(r"[a-f0-9]{32}", render_id):
        raise HTTPException(422, "Invalid render id.")
    init_studio_db()
    with _connect() as db:
        row = db.execute("SELECT * FROM studio_renders WHERE id=?", (render_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Studio render not found.")
    result = dict(row)
    if result.get("result_json"):
        result["result"] = json.loads(result.pop("result_json"))
    else:
        result.pop("result_json", None)
    if result.get("output_name"):
        result["output_url"] = "/api/v1/studio/renders/" + render_id + "/output"
    return result


@router.get("/studio/renders/{render_id}/output")
def studio_render_output(render_id: str):
    status = studio_render_status(render_id)
    if status["status"] != "completed" or not status.get("output_name"):
        raise HTTPException(409, "Studio render is not complete.")
    root = _render_output_dir().resolve()
    path = (root / status["output_name"]).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(410, "Rendered video is unavailable.")
    return FileResponse(path, media_type="video/mp4", filename="goflow-" + render_id[:8] + ".mp4")


@router.get("/studio/comfy/jobs/{prompt_id}")
def comfy_job_status(prompt_id: str):
    try:
        history = comfy_history(prompt_id)
    except (ComfyUIError, ValueError) as exc:
        raise HTTPException(502 if isinstance(exc, ComfyUIError) else 422, str(exc)) from exc
    record = history.get(prompt_id)
    if not record:
        return {"prompt_id": prompt_id, "status": "queued_or_running", "history": None}
    execution = record.get("status", {})
    outputs = record.get("outputs", {})
    imported = []
    if execution.get("completed") and isinstance(outputs, dict):
        try:
            imported = _import_comfy_outputs(prompt_id, outputs)
        except (ComfyUIError, ValueError) as exc:
            raise HTTPException(502, str(exc)) from exc
    return {"prompt_id": prompt_id, "status": "completed" if execution.get("completed") else "processing_or_failed",
            "execution_status": execution, "outputs": outputs, "imported_media": imported}
