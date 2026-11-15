"""Fixed-origin ComfyUI API client; never accepts a target URL from the browser."""
from __future__ import annotations
import os, re
from typing import Any
import httpx

class ComfyUIError(RuntimeError):
    pass

def base_url() -> str:
    return os.getenv("GOFLOW_COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")

def _client() -> httpx.Client:
    return httpx.Client(timeout=httpx.Timeout(30.0, read=120.0))

def submit_prompt(workflow: dict[str, Any], client_id: str | None = None) -> dict[str, Any]:
    if not workflow or len(workflow) > 1000:
        raise ValueError("Workflow must contain between 1 and 1000 nodes.")
    for node_id, node in workflow.items():
        if not isinstance(node_id, str) or not isinstance(node, dict):
            raise ValueError("Workflow must be a ComfyUI API-format node map.")
        if not isinstance(node.get("class_type"), str) or not isinstance(node.get("inputs"), dict):
            raise ValueError(f"Node {node_id} must contain class_type and inputs.")
    payload: dict[str, Any] = {"prompt": workflow}
    if client_id:
        payload["client_id"] = client_id[:128]
    try:
        with _client() as client:
            response = client.post(f"{base_url()}/prompt", json=payload)
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError as exc:
        raise ComfyUIError(f"Could not submit workflow to ComfyUI: {exc}") from exc
    if not result.get("prompt_id"):
        raise ComfyUIError("ComfyUI did not return a prompt_id.")
    return result

def get_history(prompt_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", prompt_id):
        raise ValueError("Invalid ComfyUI prompt ID.")
    try:
        with _client() as client:
            response = client.get(f"{base_url()}/history/{prompt_id}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise ComfyUIError(f"Could not read ComfyUI job history: {exc}") from exc

def get_queue() -> dict[str, Any]:
    try:
        with _client() as client:
            response = client.get(f"{base_url()}/queue")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise ComfyUIError(f"Could not read ComfyUI queue: {exc}") from exc
