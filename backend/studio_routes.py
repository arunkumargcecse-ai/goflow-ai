"""Authenticated Studio orchestration routes for goflow.ai.

The default generation adapter is deliberately offline/mock: it never claims to
create media and never makes a billable network request.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from generation_providers import GenerationRequest, submit_generation
from comfyui_client import ComfyUIError, download_output as comfy_download_output, get_history as comfy_history, get_queue as comfy_queue, submit_prompt as comfy_submit, upload_image as comfy_upload_image
from story_engine import StoryPlanRequest, create_story_plan as build_story_plan
from workflow_catalog import list_workflows
from workflow_registry import WorkflowRegistryError, build_workflow_prompt, get_workflow_form, list_local_workflows

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
            "available": bool(_which("piper") or _which("espeak-ng") or _which("espeak")),
            "local_engines": [name for name in ("piper", "espeak-ng", "espeak") if _which(name)],
            "note": "Local voice engines require a separately installed Tamil voice model.",
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
