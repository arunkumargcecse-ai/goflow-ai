import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import main


class StudioOrchestrationApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "GOFLOW_API_KEY": "studio-test-key",
            "GOFLOW_DATA_DIR": self.temp_dir.name,
            "GOFLOW_GENERATION_PROVIDER": "mock",
        })
        self.env.start()
        self.client = TestClient(main.app)
        self.headers = {"X-Goflow-Key": "studio-test-key"}

    def tearDown(self):
        self.client.close()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_story_plan_requires_authentication(self):
        response = self.client.post("/api/v1/story/plan", json={"idea": "A mysterious phone call"})
        self.assertEqual(response.status_code, 401)

    def test_story_plan_returns_offline_editable_scenes(self):
        response = self.client.post(
            "/api/v1/story/plan",
            headers=self.headers,
            json={"idea": "A mysterious phone call changes a young man's life", "scene_count": 6},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["engine"], "offline_template")
        self.assertEqual(len(payload["scenes"]), 6)
        self.assertEqual(sum(s["duration_seconds"] for s in payload["scenes"]), 55)
        self.assertTrue(payload["creator_review_required"])

    def test_mock_generation_is_explicit_and_persisted(self):
        response = self.client.post(
            "/api/v1/generations",
            headers=self.headers,
            json={
                "media_type": "image",
                "request": {
                    "project_id": "last-phone-call",
                    "scene_id": "scene-1",
                    "prompt": "Cinematic rainy street at midnight, vertical frame",
                    "aspect_ratio": "9:16",
                },
            },
        )
        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["status"], "mock")
        self.assertIn("no media was generated", payload["error"])
        record = self.client.get(
            "/api/v1/generations/" + payload["generation_id"], headers=self.headers
        )
        self.assertEqual(record.status_code, 200)
        self.assertEqual(record.json()["result"]["provider"], "mock")

    def test_generation_status_requires_authentication(self):
        response = self.client.get("/api/v1/generations/not-a-real-id")
        self.assertEqual(response.status_code, 401)


    @patch("studio_routes.comfy_upload_image")
    def test_comfy_reference_image_upload_returns_local_image_reference(self, upload):
        upload.return_value = {"image_ref": "goflow/reference.png", "name": "reference.png", "subfolder": "goflow", "type": "input"}
        response = self.client.post(
            "/api/v1/studio/comfy/upload-image", headers=self.headers,
            files={"file": ("reference.png", b"fake-png-bytes", "image/png")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["image_ref"], "goflow/reference.png")

    def test_comfy_reference_image_upload_rejects_unsupported_media(self):
        response = self.client.post(
            "/api/v1/studio/comfy/upload-image", headers=self.headers,
            files={"file": ("payload.txt", b"not-an-image", "text/plain")},
        )
        self.assertEqual(response.status_code, 415)

    def test_comfy_reference_image_upload_requires_authentication(self):
        response = self.client.post(
            "/api/v1/studio/comfy/upload-image",
            files={"file": ("reference.png", b"fake-png-bytes", "image/png")},
        )
        self.assertEqual(response.status_code, 401)

    @patch("studio_routes.comfy_submit")
    def test_comfy_workflow_submission_returns_prompt_id(self, submit):
        submit.return_value = {"prompt_id": "prompt-123"}
        response = self.client.post("/api/v1/studio/comfy/submit", headers=self.headers,
            json={"workflow": {"1": {"class_type": "SaveImage", "inputs": {}}}})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["prompt_id"], "prompt-123")

    def test_comfy_workflow_submission_rejects_invalid_node_graph(self):
        response = self.client.post("/api/v1/studio/comfy/submit", headers=self.headers,
            json={"workflow": {"1": {"inputs": {}}}})
        self.assertEqual(response.status_code, 422)

    @patch("studio_routes.comfy_queue")
    def test_comfy_status_reports_queue(self, queue):
        queue.return_value = {"queue_running": [], "queue_pending": []}
        response = self.client.get("/api/v1/studio/comfy/status", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["available"])

    def test_workflow_catalog_is_curated_and_never_claims_unregistered_graphs_are_ready(self):
        response = self.client.get("/api/v1/studio/workflows", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 5)
        self.assertEqual(payload["ready_count"], 0)
        self.assertTrue(all(item["ready"] is False for item in payload["workflows"]))
        self.assertTrue(all(item["workflow_id"] is None for item in payload["workflows"]))

    def test_workflow_catalog_category_filter(self):
        response = self.client.get("/api/v1/studio/workflows?category=video", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual({item["category"] for item in response.json()["workflows"]}, {"video"})

    def test_workflow_catalog_lists_imported_local_apps(self):
        response = self.client.get("/api/v1/studio/workflows", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["local_count"], 3)
        self.assertEqual({item["id"] for item in payload["local_workflows"]},
                         {"create-image", "sfx", "music"})

    @patch("studio_routes.get_workflow_form")
    def test_local_workflow_form_returns_manifest_fields(self, get_form):
        get_form.return_value = {"id": "sample-image", "inputs": [{"id": "prompt"}], "ready": True}
        response = self.client.get("/api/v1/studio/workflows/sample-image", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["inputs"][0]["id"], "prompt")

    @patch("studio_routes.comfy_submit")
    @patch("studio_routes.build_workflow_prompt")
    def test_local_workflow_run_builds_and_submits_registered_graph(self, build_prompt, submit):
        build_prompt.return_value = (
            {"1": {"class_type": "SaveImage", "inputs": {}}},
            {"id": "sample-image", "name": "Sample image"},
        )
        submit.return_value = {"prompt_id": "local-prompt-1"}
        response = self.client.post(
            "/api/v1/studio/workflows/sample-image/run",
            headers=self.headers,
            json={"values": {"prompt": "A rainy street"}},
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["prompt_id"], "local-prompt-1")
        build_prompt.assert_called_once_with("sample-image", {"prompt": "A rainy street"})

    @patch("studio_routes.comfy_download_output")
    @patch("studio_routes.comfy_history")
    def test_completed_comfy_outputs_are_imported_and_downloadable(self, history, download):
        history.return_value = {
            "prompt-output-1": {
                "status": {"completed": True},
                "outputs": {"9": {"images": [{"filename": "render.png", "subfolder": "", "type": "output"}]}},
            }
        }
        download.return_value = (b"fake-image-bytes", "image/png")
        status = self.client.get(
            "/api/v1/studio/comfy/jobs/prompt-output-1", headers=self.headers
        )
        self.assertEqual(status.status_code, 200)
        imported = status.json()["imported_media"]
        self.assertEqual(len(imported), 1)
        media = self.client.get(imported[0]["url"], headers=self.headers)
        self.assertEqual(media.status_code, 200)
        self.assertEqual(media.content, b"fake-image-bytes")
        self.assertEqual(media.headers["content-type"], "image/png")

    @patch("studio_routes.comfy_download_output")
    @patch("studio_routes.comfy_history")
    def test_comfy_output_import_is_idempotent_on_status_poll(self, history, download):
        history.return_value = {
            "prompt-output-2": {
                "status": {"completed": True},
                "outputs": {"9": {"images": [{"filename": "render.png", "subfolder": "", "type": "output"}]}},
            }
        }
        download.return_value = (b"fake-image-bytes", "image/png")
        first = self.client.get("/api/v1/studio/comfy/jobs/prompt-output-2", headers=self.headers)
        second = self.client.get("/api/v1/studio/comfy/jobs/prompt-output-2", headers=self.headers)
        self.assertEqual(first.json()["imported_media"][0]["media_id"], second.json()["imported_media"][0]["media_id"])
        download.assert_called_once()

    def test_generated_media_download_requires_authentication(self):
        response = self.client.get("/api/v1/studio/media/" + "a" * 32)
        self.assertEqual(response.status_code, 401)

    def test_provider_capabilities_never_claim_mock_media_is_real(self):
        response = self.client.get("/api/v1/studio/providers", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["image"]["creates_media"])
        self.assertFalse(response.json()["video"]["creates_media"])


if __name__ == "__main__":
    unittest.main()
