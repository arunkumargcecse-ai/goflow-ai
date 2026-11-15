"""Build an editable ComfyUI UI-workflow export from the pinned Wan Animate template.

This intentionally exports the ComfyUI canvas workflow JSON, not an API prompt.
The user reviews the graph in ComfyUI and starts inference there.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

_SAFE_REF = re.compile(r"^[A-Za-z0-9_.-]{1,160}(?:/[A-Za-z0-9_.-]{1,160})?$")
_REQUIRED_NODES = {145: "LoadVideo", 10: "LoadImage", 21: "CLIPTextEncode"}


class WanWorkflowExportError(ValueError):
    pass


def build_wan_animate_ui_workflow(
    template_path: Path, video_ref: str, image_ref: str, prompt: str
) -> dict[str, Any]:
    """Return a copy of the official UI graph with uploaded assets and prompt bound."""
    for label, value in (("video", video_ref), ("image", image_ref)):
        if not isinstance(value, str) or not _SAFE_REF.fullmatch(value) or ".." in value.split("/"):
            raise WanWorkflowExportError(f"Invalid ComfyUI {label} reference.")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4000:
        raise WanWorkflowExportError("Prompt must contain 1–4000 characters.")
    try:
        graph = json.loads(Path(template_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WanWorkflowExportError("The bundled Wan Animate workflow template is unavailable or invalid.") from exc
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
        raise WanWorkflowExportError("The bundled workflow is not a ComfyUI canvas workflow.")
    nodes = {node.get("id"): node for node in graph["nodes"] if isinstance(node, dict)}
    for node_id, expected_type in _REQUIRED_NODES.items():
        node = nodes.get(node_id)
        if not node or node.get("type") != expected_type or not isinstance(node.get("widgets_values"), list):
            raise WanWorkflowExportError(f"Wan template node {node_id} ({expected_type}) changed; export was stopped.")
    nodes[145]["widgets_values"][0] = video_ref
    nodes[10]["widgets_values"][0] = image_ref
    nodes[21]["widgets_values"][0] = prompt.strip()
    return copy.deepcopy(graph)
