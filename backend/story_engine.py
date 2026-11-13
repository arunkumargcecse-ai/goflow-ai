"""Provider-optional story and storyboard planning for goflow.ai.

The deterministic planner is always available offline. An OpenAI-compatible
chat endpoint can be enabled by setting GOFLOW_LLM_BASE_URL, GOFLOW_LLM_MODEL,
and GOFLOW_LLM_API_KEY on the backend. No secrets belong in the browser.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field, field_validator


class StoryPlanRequest(BaseModel):
    idea: str = Field(min_length=8, max_length=5000)
    language: str = Field(default="Tamil", min_length=2, max_length=40)
    target_duration_seconds: int = Field(default=55, ge=15, le=600)
    aspect_ratio: str = Field(default="9:16", pattern=r"^(9:16|16:9|1:1)$")
    genre: str = Field(default="mystery", max_length=80)
    tone: str = Field(default="cinematic", max_length=120)
    audience: str = Field(default="general", max_length=120)
    character_notes: str = Field(default="", max_length=2000)
    location_notes: str = Field(default="", max_length=2000)
    visual_style: str = Field(default="cinematic realism", max_length=200)
    scene_count: int = Field(default=6, ge=2, le=30)

    @field_validator("idea")
    @classmethod
    def idea_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("idea must contain meaningful text")
        return value.strip()


def _duration_split(total: int, count: int) -> list[int]:
    base, remainder = divmod(total, count)
    return [base + (1 if i < remainder else 0) for i in range(count)]


def _offline_plan(request: StoryPlanRequest) -> dict[str, Any]:
    """Create an editable structured outline without claiming it is AI-generated."""
    durations = _duration_split(request.target_duration_seconds, request.scene_count)
    beats = [
        ("Opening hook", "Open with a striking image or unanswered question."),
        ("Set-up", "Establish the protagonist, setting, and immediate objective."),
        ("First clue", "Introduce a concrete clue that changes the audience's expectation."),
        ("Escalation", "Raise the stakes and tighten the visual pacing."),
        ("Reveal", "Deliver the central reveal with a clear visual payoff."),
        ("Final sting", "End on a memorable image, emotional beat, or twist."),
    ]
    scenes = []
    for index in range(request.scene_count):
        beat, direction = beats[index] if index < len(beats) else (
            f"Story beat {index + 1}", "Advance the story while preserving continuity."
        )
        scenes.append({
            "scene_number": index + 1,
            "title": beat,
            "duration_seconds": durations[index],
            "purpose": direction,
            "visual_description": f"{direction} Story idea: {request.idea}",
            "camera_direction": "Cinematic medium shot; deliberate camera movement; motivated close-up.",
            "dialogue": "",
            "voiceover": "",
            "sound_design": "Use restrained ambience and a focused sound cue; avoid overpowering dialogue.",
            "image_prompt": (
                f"{request.visual_style}, {request.genre}, {request.tone}. "
                f"Scene {index + 1}: {direction} Story: {request.idea}. "
                f"Aspect ratio {request.aspect_ratio}. Maintain consistent characters and locations. "
                "No text, subtitles, logos, watermarks, or extra fingers."
            ),
            "video_prompt": (
                f"Create a {durations[index]} second cinematic shot. {direction} "
                f"Camera: slow intentional movement, natural motion, stable subject identity. "
                f"Visual style: {request.visual_style}. Story context: {request.idea}"
            ),
            "continuity": {
                "character_notes": request.character_notes,
                "location_notes": request.location_notes,
                "visual_style": request.visual_style,
                "wardrobe_and_props": "Keep wardrobe, props, age, face, and lighting consistent across scenes.",
            },
            "status": "draft",
        })
    return {
        "engine": "offline_template",
        "requires_provider": False,
        "project": {
            "idea": request.idea,
            "language": request.language,
            "genre": request.genre,
            "tone": request.tone,
            "audience": request.audience,
            "target_duration_seconds": request.target_duration_seconds,
            "aspect_ratio": request.aspect_ratio,
            "visual_style": request.visual_style,
        },
        "logline": request.idea,
        "synopsis": (
            f"A {request.genre} story in {request.language}, shaped for a "
            f"{request.target_duration_seconds}-second {request.aspect_ratio} video."
        ),
        "characters": [{"name": "Protagonist", "description": request.character_notes or "Creator-defined; maintain the same identity in every scene."}],
        "locations": [{"name": "Primary location", "description": request.location_notes or "Creator-defined; maintain spatial continuity."}],
        "scenes": scenes,
        "creator_review_required": True,
        "notice": "Offline planning scaffold. Replace draft beats and dialogue with creator-approved story content.",
    }


def _llm_plan(request: StoryPlanRequest) -> dict[str, Any]:
    base_url = os.getenv("GOFLOW_LLM_BASE_URL", "").rstrip("/")
    model = os.getenv("GOFLOW_LLM_MODEL", "")
    api_key = os.getenv("GOFLOW_LLM_API_KEY", "")
    if not (base_url and model and api_key):
        return _offline_plan(request)
    payload = {
        "model": model,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": (
                "You are a film pre-production planner. Return only valid JSON with keys "
                "logline, synopsis, characters, locations, scenes. Each scene must include "
                "scene_number, title, duration_seconds, purpose, visual_description, "
                "camera_direction, dialogue, voiceover, sound_design, image_prompt, "
                "video_prompt, continuity. Keep durations summing to the requested duration. "
                "Use the requested language for dialogue and voiceover. Do not invent real people."
            )},
            {"role": "user", "content": json.dumps(request.model_dump(), ensure_ascii=False)},
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    endpoint = base_url if base_url.endswith("/chat/completions") else base_url + "/chat/completions"
    req = Request(endpoint, data=body, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }, method="POST")
    try:
        with urlopen(req, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        plan = json.loads(content)
        if not isinstance(plan.get("scenes"), list) or not plan["scenes"]:
            raise ValueError("LLM response did not contain scenes")
        plan.update({
            "engine": "openai_compatible",
            "requires_provider": True,
            "project": request.model_dump(),
            "creator_review_required": True,
        })
        return plan
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Story provider request failed: {type(exc).__name__}") from exc


def create_story_plan(request: StoryPlanRequest) -> dict[str, Any]:
    """Generate a provider-backed plan when configured, otherwise an offline draft."""
    return _llm_plan(request)
