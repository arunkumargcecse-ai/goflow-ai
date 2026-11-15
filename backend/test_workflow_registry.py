import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow_registry import (
    WorkflowRegistryError,
    build_workflow_prompt,
    get_workflow_form,
)


class LocalWorkflowRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"GOFLOW_WORKFLOW_DIR": self.temp.name})
        self.env.start()
        app = Path(self.temp.name) / "sample-image"
        app.mkdir()
        manifest = {
            "id": "sample-image",
            "name": "Sample image",
            "section": "image",
            "status": "ready",
            "workflow": "workflow.api.json",
            "summary": "A small local test graph",
            "inputs": [
                {"id": "prompt", "type": "text", "label": "Prompt", "required": True,
                 "bind": [{"node": "1", "field": "text"}]},
                {"id": "steps", "type": "number", "label": "Steps", "default": 20,
                 "min": 1, "max": 50, "bind": [{"node": "1", "field": "steps"}]},
                {"id": "resolution", "type": "select", "label": "Resolution", "default": 1,
                 "options": [{"value": 1, "label": "1K"}, {"value": 2, "label": "2K"}],
                 "bind": [{"node": "1", "field": "resolution"}]},
                {"id": "aspect", "type": "select", "label": "Aspect", "default": "1:1",
                 "options": [{"value": "9:16", "label": "Vertical", "sets": [
                     {"node": "2", "field": "width", "value": 768},
                     {"node": "2", "field": "height", "value": 1344}
                 ]}]},
            ],
            "outputs": [{"node": "2", "type": "image"}],
            "models": [{"repo": "example/model", "file": "model.safetensors",
                        "dir": "checkpoints", "gb": 1.0, "phase": "all",
                        "license": "verify upstream model license"}],
            "custom_nodes": [],
        }
        graph = {
            "1": {"class_type": "TestSampler", "inputs": {"text": "", "steps": 1}},
            "2": {"class_type": "SaveImage", "inputs": {"images": ["1", 0], "width": 1024, "height": 1024}},
        }
        (app / "app.json").write_text(json.dumps(manifest), encoding="utf-8")
        (app / "workflow.api.json").write_text(json.dumps(graph), encoding="utf-8")

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_manifest_exposes_dynamic_form_and_model_license(self):
        form = get_workflow_form("sample-image")
        self.assertEqual(form["inputs"][0]["id"], "prompt")
        self.assertEqual(form["models"][0]["license"], "verify upstream model license")
        self.assertEqual(form["cost_mode"], "local_only")

    def test_builds_graph_from_manifest_bindings(self):
        graph, manifest = build_workflow_prompt("sample-image", {"prompt": "rainy street"})
        self.assertEqual(graph["1"]["inputs"]["text"], "rainy street")
        self.assertEqual(graph["1"]["inputs"]["steps"], 20)
        self.assertEqual(graph["1"]["inputs"]["resolution"], 1)
        self.assertEqual(manifest["id"], "sample-image")
        vertical, _ = build_workflow_prompt("sample-image", {"prompt": "rainy street", "aspect": "9:16"})
        self.assertEqual(vertical["2"]["inputs"]["width"], 768)
        self.assertEqual(vertical["2"]["inputs"]["height"], 1344)

    def test_rejects_unknown_inputs_and_out_of_range_values(self):
        with self.assertRaises(WorkflowRegistryError):
            build_workflow_prompt("sample-image", {"prompt": "ok", "arbitrary": "node injection"})
        with self.assertRaises(WorkflowRegistryError):
            build_workflow_prompt("sample-image", {"prompt": "ok", "steps": 999})

    def test_rejects_missing_required_input(self):
        with self.assertRaises(WorkflowRegistryError):
            build_workflow_prompt("sample-image", {})

    def test_rejects_path_traversal_and_unready_apps(self):
        with self.assertRaises(WorkflowRegistryError):
            get_workflow_form("../sample-image")
        app = Path(self.temp.name) / "sample-image"
        manifest = json.loads((app / "app.json").read_text(encoding="utf-8"))
        manifest["status"] = "draft"
        (app / "app.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(WorkflowRegistryError):
            get_workflow_form("sample-image")


if __name__ == "__main__":
    unittest.main()
