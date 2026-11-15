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


def upload_image(filename: str, content_type: str, data: bytes) -> dict[str, str]:
    """Upload a validated image to the configured local ComfyUI input directory."""
    allowed = {"image/png", "image/jpeg", "image/webp"}
    if content_type not in allowed:
        raise ValueError("Only PNG, JPEG, and WebP reference images are supported.")
    if not data or len(data) > 20 * 1024 * 1024:
        raise ValueError("Reference image must be between 1 byte and 20 MB.")
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename.rsplit("/", 1)[-1].rsplit("\\\\", 1)[-1])[:120]
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError("Invalid reference image filename.")
    try:
        with _client() as client:
            response = client.post(
                f"{base_url()}/upload/image",
                files={"image": (safe_name, data, content_type)},
                data={"type": "input", "overwrite": "false"},
            )
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError as exc:
        raise ComfyUIError(f"Could not upload reference image to ComfyUI: {exc}") from exc
    name, subfolder = result.get("name"), result.get("subfolder", "")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", name):
        raise ComfyUIError("ComfyUI returned an invalid uploaded image name.")
    if not isinstance(subfolder, str) or (subfolder and not re.fullmatch(r"[A-Za-z0-9_./-]{1,160}", subfolder)):
        raise ComfyUIError("ComfyUI returned an invalid image subfolder.")
    image_ref = f"{subfolder}/{name}" if subfolder else name
    if ".." in image_ref.split("/"):
        raise ComfyUIError("ComfyUI returned an unsafe image path.")
    return {"image_ref": image_ref, "name": name, "subfolder": subfolder, "type": result.get("type", "input")}



def upload_video(filename: str, content_type: str, data: bytes) -> dict[str, str]:
    """Upload a validated reference video into the configured local ComfyUI input folder."""
    allowed = {"video/mp4", "video/webm", "video/quicktime"}
    if content_type not in allowed:
        raise ValueError("Only MP4, WebM, and QuickTime reference videos are supported.")
    if not data or len(data) > 100 * 1024 * 1024:
        raise ValueError("Reference video must be between 1 byte and 100 MB.")
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename.rsplit("/", 1)[-1].rsplit(chr(92), 1)[-1])[:120]
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError("Invalid reference video filename.")
    try:
        with _client() as client:
            response = client.post(
                f"{base_url()}/upload/image",
                files={"image": (safe_name, data, content_type)},
                data={"type": "input", "overwrite": "false"},
            )
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError as exc:
        raise ComfyUIError(f"Could not upload reference video to ComfyUI: {exc}") from exc
    name, subfolder = result.get("name"), result.get("subfolder", "")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", name):
        raise ComfyUIError("ComfyUI returned an invalid uploaded video name.")
    if not isinstance(subfolder, str) or (subfolder and not re.fullmatch(r"[A-Za-z0-9_./-]{1,160}", subfolder)):
        raise ComfyUIError("ComfyUI returned an invalid video subfolder.")
    video_ref = f"{subfolder}/{name}" if subfolder else name
    if ".." in video_ref.split("/"):
        raise ComfyUIError("ComfyUI returned an unsafe uploaded video path.")
    return {"video_ref": video_ref, "name": name, "subfolder": subfolder, "type": result.get("type", "input")}


def download_output(filename: str, subfolder: str = "", output_type: str = "output") -> tuple[bytes, str]:
    """Download a ComfyUI output using validated view parameters, never a browser URL."""
    if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,180}", filename) or filename in {".", ".."}:
        raise ValueError("Invalid ComfyUI output filename.")
    if not isinstance(subfolder, str) or (subfolder and (
        len(subfolder) > 180 or not re.fullmatch(r"[A-Za-z0-9_./-]+", subfolder)
        or any(part in {"", ".", ".."} for part in subfolder.split("/"))
    )):
        raise ValueError("Invalid ComfyUI output subfolder.")
    if output_type not in {"output", "temp"}:
        raise ValueError("Only ComfyUI output and temporary media are supported.")
    try:
        with _client() as client:
            response = client.get(
                f"{base_url()}/view",
                params={"filename": filename, "subfolder": subfolder, "type": output_type},
                timeout=httpx.Timeout(30.0, read=300.0),
            )
            response.raise_for_status()
            if len(response.content) > 500 * 1024 * 1024:
                raise ComfyUIError("ComfyUI output exceeds the 500 MB import limit.")
            return response.content, response.headers.get("content-type", "application/octet-stream")
    except httpx.HTTPError as exc:
        raise ComfyUIError(f"Could not download ComfyUI output: {exc}") from exc
