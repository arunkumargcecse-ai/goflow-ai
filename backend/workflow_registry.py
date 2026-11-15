"""Load and validate local Freefield-compatible ComfyUI app manifests.

Only explicitly installed local app folders are considered. This module never
downloads models/workflows and never trusts browser-supplied graph JSON.
"""
from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from typing import Any

_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_INPUT_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_SUPPORTED_INPUTS = {"text", "textarea", "number", "slider", "select", "toggle", "seed"}


class WorkflowRegistryError(ValueError):
    pass


def workflow_root() -> Path:
    configured = os.getenv("GOFLOW_WORKFLOW_DIR")
    return Path(configured).expanduser().resolve() if configured else (Path(__file__).parent / "workflows").resolve()


def _safe_app_dir(workflow_id: str) -> Path:
    if not _ID.fullmatch(workflow_id):
        raise WorkflowRegistryError("Invalid workflow id.")
    root = workflow_root()
    app_dir = (root / workflow_id).resolve()
    if app_dir.parent != root:
        raise WorkflowRegistryError("Workflow path is outside the local registry.")
    return app_dir


def _read_app(workflow_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    app_dir = _safe_app_dir(workflow_id)
    manifest_path = app_dir / "app.json"
    if not manifest_path.is_file():
        raise WorkflowRegistryError("Workflow is not installed in the local registry.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowRegistryError("Workflow manifest is unreadable or invalid JSON.") from exc
    if not isinstance(manifest, dict) or manifest.get("id") != workflow_id:
        raise WorkflowRegistryError("Manifest id must match its folder.")
    if manifest.get("status") != "ready":
        raise WorkflowRegistryError("Workflow manifest is not marked ready.")
    workflow_name = manifest.get("workflow", "workflow.api.json")
    if not isinstance(workflow_name, str) or not workflow_name.endswith(".api.json") or Path(workflow_name).name != workflow_name:
        raise WorkflowRegistryError("Manifest workflow must be a local .api.json filename.")
    graph_path = (app_dir / workflow_name).resolve()
    if graph_path.parent != app_dir or not graph_path.is_file():
        raise WorkflowRegistryError("Local API workflow file is missing.")
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowRegistryError("Workflow graph is unreadable or invalid JSON.") from exc
    if not isinstance(graph, dict) or not graph or len(graph) > 1000:
        raise WorkflowRegistryError("Workflow graph must be a non-empty ComfyUI API node map.")
    for node_id, node in graph.items():
        if not isinstance(node_id, str) or not isinstance(node, dict) or not isinstance(node.get("class_type"), str) or not isinstance(node.get("inputs"), dict):
            raise WorkflowRegistryError(f"Invalid ComfyUI API node: {node_id}.")
    _validate_manifest_bindings(manifest, graph)
    return manifest, graph


def _validate_manifest_bindings(manifest: dict[str, Any], graph: dict[str, Any]) -> None:
    inputs = manifest.get("inputs", [])
    if not isinstance(inputs, list):
        raise WorkflowRegistryError("Manifest inputs must be an array.")
    seen: set[str] = set()
    for item in inputs:
        if not isinstance(item, dict):
            raise WorkflowRegistryError("Each manifest input must be an object.")
        input_id = item.get("id")
        if not isinstance(input_id, str) or not _INPUT_ID.fullmatch(input_id) or input_id in seen:
            raise WorkflowRegistryError("Manifest input ids must be unique snake_case identifiers.")
        seen.add(input_id)
        if item.get("type") not in _SUPPORTED_INPUTS:
            raise WorkflowRegistryError(f"Input type '{item.get('type')}' is not supported by this runner yet.")
        for binding in item.get("bind", []):
            if not isinstance(binding, dict):
                raise WorkflowRegistryError(f"Invalid binding for input '{input_id}'.")
            node_id, field = binding.get("node"), binding.get("field")
            if node_id not in graph or not isinstance(field, str) or field not in graph[node_id]["inputs"]:
                raise WorkflowRegistryError(f"Binding for '{input_id}' does not resolve to a workflow node input.")
    for output in manifest.get("outputs", []):
        if not isinstance(output, dict) or output.get("node") not in graph:
            raise WorkflowRegistryError("Every declared output must reference an existing workflow node.")


def get_workflow_form(workflow_id: str) -> dict[str, Any]:
    manifest, _ = _read_app(workflow_id)
    return {
        "id": manifest["id"],
        "name": manifest.get("name", manifest["id"]),
        "section": manifest.get("section", "utility"),
        "summary": manifest.get("summary", ""),
        "inputs": copy.deepcopy(manifest.get("inputs", [])),
        "outputs": copy.deepcopy(manifest.get("outputs", [])),
        "models": copy.deepcopy(manifest.get("models", [])),
        "custom_nodes": copy.deepcopy(manifest.get("custom_nodes", [])),
        "vram": copy.deepcopy(manifest.get("vram", {})),
        "source": copy.deepcopy(manifest.get("source", {})),
        "cost_mode": "local_only",
        "ready": True,
    }


def build_workflow_prompt(workflow_id: str, values: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest, graph = _read_app(workflow_id)
    declared = {item["id"]: item for item in manifest.get("inputs", [])}
    unknown = set(values) - set(declared)
    if unknown:
        raise WorkflowRegistryError("Unknown workflow input(s): " + ", ".join(sorted(unknown)))
    resolved: dict[str, Any] = {}
    for input_id, item in declared.items():
        value = values.get(input_id, item.get("default"))
        if value is None and item.get("required", False):
            raise WorkflowRegistryError(f"Input '{input_id}' is required.")
        if value is None:
            continue
        kind = item["type"]
        if kind in {"text", "textarea", "select"} and not isinstance(value, str):
            raise WorkflowRegistryError(f"Input '{input_id}' must be text.")
        if kind in {"number", "slider", "seed"} and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise WorkflowRegistryError(f"Input '{input_id}' must be numeric.")
        if kind == "toggle" and not isinstance(value, bool):
            raise WorkflowRegistryError(f"Input '{input_id}' must be boolean.")
        if kind in {"number", "slider", "seed"}:
            if "min" in item and value < item["min"] or "max" in item and value > item["max"]:
                raise WorkflowRegistryError(f"Input '{input_id}' is outside its allowed range.")
        if kind == "select":
            options = item.get("options", [])
            allowed = [option.get("value") for option in options if isinstance(option, dict)]
            if allowed and value not in allowed:
                raise WorkflowRegistryError(f"Input '{input_id}' is not an allowed option.")
        resolved[input_id] = value

    for input_id, item in declared.items():
        if input_id not in resolved:
            continue
        value = resolved[input_id]
        for binding in item.get("bind", []):
            node_id, field = binding["node"], binding["field"]
            template = binding.get("template")
            if isinstance(template, str):
                replacement = template
                for key, replacement_value in resolved.items():
                    replacement = replacement.replace("{" + key + "}", str(replacement_value))
                value_to_write = replacement.replace("{" + input_id + "}", str(value))
            else:
                value_to_write = value
            graph[node_id]["inputs"][field] = value_to_write
        if item["type"] == "select":
            option = next((entry for entry in item.get("options", []) if isinstance(entry, dict) and entry.get("value") == value), None)
            if option:
                for setting in option.get("sets", []):
                    node_id, field = setting.get("node"), setting.get("field")
                    if node_id not in graph or field not in graph[node_id]["inputs"]:
                        raise WorkflowRegistryError("Select option writes to an unknown workflow input.")
                    setting_value = setting.get("value")
                    if isinstance(setting_value, str):
                        for key, replacement_value in resolved.items():
                            setting_value = setting_value.replace("{" + key + "}", str(replacement_value))
                    graph[node_id]["inputs"][field] = setting_value
    return graph, manifest
