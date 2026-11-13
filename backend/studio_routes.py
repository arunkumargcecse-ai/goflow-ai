"""Authenticated Studio orchestration routes for goflow.ai.

The default generation adapter is deliberately offline/mock: it never claims to
create media and never makes a billable network request.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from generation_providers import GenerationRequest, submit_generation
from story_engine import StoryPlanRequest, create_story_plan

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
        db.commit()


class GenerationSubmission(BaseModel):
    media_type: Literal["image", "video"]
    request: GenerationRequest


@router.post("/story/plan")
def create_story_plan(request: StoryPlanRequest):
    """Generate an editable offline-first story and storyboard plan."""
    return create_story_plan(request)


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
