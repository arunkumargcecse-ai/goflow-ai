import json
import tempfile
import unittest
from pathlib import Path

from wan_workflow_export import WanWorkflowExportError, build_wan_animate_ui_workflow


class WanWorkflowExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.template = Path(self.temp.name) / "template.json"
        self.template.write_text(json.dumps({"nodes": [
            {"id": 145, "type": "LoadVideo", "widgets_values": ["old.mp4", "image"]},
            {"id": 10, "type": "LoadImage", "widgets_values": ["old.png", "image"]},
            {"id": 21, "type": "CLIPTextEncode", "widgets_values": ["old prompt"]},
        ]}), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_binds_video_image_and_prompt_without_mutating_template(self):
        result = build_wan_animate_ui_workflow(self.template, "input/ref.mp4", "input/person.png", "Cinematic shot")
        nodes = {node["id"]: node for node in result["nodes"]}
        self.assertEqual(nodes[145]["widgets_values"][0], "input/ref.mp4")
        self.assertEqual(nodes[10]["widgets_values"][0], "input/person.png")
        self.assertEqual(nodes[21]["widgets_values"][0], "Cinematic shot")
        original = json.loads(self.template.read_text(encoding="utf-8"))
        self.assertEqual(original["nodes"][0]["widgets_values"][0], "old.mp4")

    def test_rejects_path_traversal(self):
        with self.assertRaises(WanWorkflowExportError):
            build_wan_animate_ui_workflow(self.template, "../outside.mp4", "person.png", "Prompt")

    def test_stops_if_template_node_contract_changes(self):
        self.template.write_text(json.dumps({"nodes": [
            {"id": 145, "type": "LoadVideo", "widgets_values": ["old.mp4"]},
            {"id": 10, "type": "LoadImage", "widgets_values": ["old.png"]},
            {"id": 21, "type": "OtherNode", "widgets_values": ["prompt"]},
        ]}), encoding="utf-8")
        with self.assertRaises(WanWorkflowExportError):
            build_wan_animate_ui_workflow(self.template, "ref.mp4", "person.png", "Prompt")


if __name__ == "__main__":
    unittest.main()
