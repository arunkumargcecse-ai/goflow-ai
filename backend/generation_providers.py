"""Provider-neutral image/video generation contracts for goflow.ai.

No provider is enabled by default. The mock provider supports safe workflow
testing without network calls or charges. Real provider adapters can be added
behind this contract without coupling the Studio to a vendor.
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=120)
    scene_id: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=8, max_length=12000)
    negative_prompt: str = Field(default="", max_length=4000)
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    duration_seconds: int = Field(default=5, ge=1, le=30)
    seed: int | None = Field(default=None, ge=0, le=2**32 - 1)
    reference_media_ids: list[str] = Field(default_factory=list, max_length=10)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerationResult(BaseModel):
    generation_id: str
    provider: str
    media_type: Literal["image", "video"]
    status: Literal["queued", "submitted", "completed", "failed", "mock"]
    provider_job_id: str | None = None
    output_url: str | None = None
    error: str | None = None
    estimated_cost: str = "unknown"
    creator_review_required: bool = True


class GenerationProvider(Protocol):
    name: str

    def submit(self, media_type: Literal["image", "video"], request: GenerationRequest) -> GenerationResult:
        ...


class MockGenerationProvider:
    """Deterministic no-network provider used for UI and orchestration tests."""
    name = "mock"

    def submit(self, media_type: Literal["image", "video"], request: GenerationRequest) -> GenerationResult:
        return GenerationResult(
            generation_id=uuid.uuid4().hex,
            provider=self.name,
            media_type=media_type,
            status="mock",
            error="Mock only: no media was generated. Configure a real provider to render assets.",
            estimated_cost="₹0 (no external request)",
        )


class OpenAICompatibleImageProvider:
    """Image adapter for endpoints implementing the OpenAI Images API shape."""
    name = "openai_compatible_images"

    def submit(self, media_type: Literal["image", "video"], request: GenerationRequest) -> GenerationResult:
        if media_type != "image":
            raise ValueError("This provider supports image generation only")
        base_url = os.getenv("GOFLOW_IMAGE_BASE_URL", "").rstrip("/")
        api_key = os.getenv("GOFLOW_IMAGE_API_KEY", "")
        model = os.getenv("GOFLOW_IMAGE_MODEL", "")
        if not (base_url and api_key and model):
            raise RuntimeError("Image provider is not configured")
        # Submission is deliberately not implemented with a guessed vendor payload.
        # Each provider must supply a tested adapter for its exact API contract.
        raise NotImplementedError(
            "Provider credentials are present, but this endpoint needs a vendor-specific tested adapter."
        )


def get_generation_provider() -> GenerationProvider:
    provider = os.getenv("GOFLOW_GENERATION_PROVIDER", "mock").strip().lower()
    if provider == "mock":
        return MockGenerationProvider()
    if provider == "openai_compatible_images":
        return OpenAICompatibleImageProvider()
    raise RuntimeError(f"Unsupported generation provider: {provider}")


def submit_generation(
    media_type: Literal["image", "video"], request: GenerationRequest
) -> GenerationResult:
    return get_generation_provider().submit(media_type, request)
