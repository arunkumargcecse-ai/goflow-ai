"""Curated, license-aware workflow catalogue for the Creator Studio.

Entries describe workflow families, not bundled model weights or executable graphs.
A workflow becomes runnable only after a local ComfyUI graph is explicitly registered.
"""
from __future__ import annotations

from copy import deepcopy

_CATALOG = [
    {
        "id": "cinematic-still",
        "name": "Cinematic still",
        "category": "image",
        "description": "Create a cinematic keyframe for a storyboard scene.",
        "inputs": ["prompt", "aspect_ratio", "seed"],
        "workflow_id": None,
        "ready": False,
        "requirements": {"worker": "ComfyUI", "models": [], "custom_nodes": []},
        "license": {"workflow": "not bundled", "models": "verify each model card"},
        "cost_mode": "local_only",
    },
    {
        "id": "image-to-video",
        "name": "Image to video",
        "category": "video",
        "description": "Animate an approved still into a short scene clip.",
        "inputs": ["image", "prompt", "duration_seconds", "camera_motion", "seed"],
        "workflow_id": None,
        "ready": False,
        "requirements": {"worker": "ComfyUI", "models": [], "custom_nodes": []},
        "license": {"workflow": "not bundled", "models": "verify each model card"},
        "cost_mode": "local_only",
    },
    {
        "id": "camera-movement",
        "name": "Camera movement",
        "category": "video",
        "description": "Apply a controlled cinematic camera move to a scene.",
        "inputs": ["image_or_video", "movement", "intensity", "duration_seconds"],
        "workflow_id": None,
        "ready": False,
        "requirements": {"worker": "ComfyUI", "models": [], "custom_nodes": []},
        "license": {"workflow": "not bundled", "models": "verify each model card"},
        "cost_mode": "local_only",
    },
    {
        "id": "sound-effects",
        "name": "Sound effects",
        "category": "audio",
        "description": "Plan and generate scene-specific ambience and effects.",
        "inputs": ["prompt", "duration_seconds"],
        "workflow_id": None,
        "ready": False,
        "requirements": {"worker": "ComfyUI", "models": [], "custom_nodes": []},
        "license": {"workflow": "not bundled", "models": "verify each model card"},
        "cost_mode": "local_only",
    },
    {
        "id": "music-bed",
        "name": "Music bed",
        "category": "audio",
        "description": "Create a background music bed for an approved edit.",
        "inputs": ["mood", "tempo", "duration_seconds"],
        "workflow_id": None,
        "ready": False,
        "requirements": {"worker": "ComfyUI", "models": [], "custom_nodes": []},
        "license": {"workflow": "not bundled", "models": "verify each model card"},
        "cost_mode": "local_only",
    },
]


def list_workflows(category: str | None = None) -> dict:
    """Return a defensive copy; never expose mutable catalogue internals."""
    entries = deepcopy(_CATALOG)
    if category:
        entries = [item for item in entries if item["category"] == category]
    return {
        "source": "goflow_curated_catalog",
        "count": len(entries),
        "ready_count": sum(1 for item in entries if item["ready"]),
        "categories": ["image", "video", "audio"],
        "workflows": entries,
        "note": "Catalogue entries are planning templates. No model is downloaded and no workflow is executable until a compatible local graph is registered.",
    }
