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

    def test_provider_capabilities_never_claim_mock_media_is_real(self):
        response = self.client.get("/api/v1/studio/providers", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["image"]["creates_media"])
        self.assertFalse(response.json()["video"]["creates_media"])


if __name__ == "__main__":
    unittest.main()
