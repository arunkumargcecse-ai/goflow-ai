"""End-to-end Creator Studio acceptance test using generated local media only.

Exercises authenticated reference upload, FFmpeg analysis, shot-map persistence,
character bible, prompt building, per-shot preview, 720p sequence render and MP4
download. No external provider or paid API is called.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
import studio_routes


class CreatorStudioEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise unittest.SkipTest("FFmpeg and ffprobe are required")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="goflow-studio-e2e-")
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {
            "GOFLOW_API_KEY": "goflow-e2e-test-key",
            "GOFLOW_DATA_DIR": str(self.root / "data"),
            "GOFLOW_GENERATION_PROVIDER": "mock",
        })
        self.env.start()
        self.client_context = TestClient(main.app)
        self.client = self.client_context
        self.headers = {"X-Goflow-Key": "goflow-e2e-test-key"}
        self._make_assets()

    def tearDown(self):
        self.client.close()
        self.env.stop()
        self.temp.cleanup()

    def _make_assets(self):
        self.reference = self.root / "reference.mp4"
        self.character = self.root / "character.png"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=24:duration=3",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(self.reference),
        ], check=True, timeout=60)
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=navy:s=320x240",
            "-frames:v", "1", str(self.character),
        ], check=True, timeout=30)

    def _wait_for_render(self, render_id: str) -> dict:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            response = self.client.get(
                f"/api/v1/studio/renders/{render_id}", headers=self.headers
            )
            self.assertEqual(response.status_code, 200, response.text)
            status = response.json()
            if status["status"] == "completed":
                return status
            if status["status"] == "failed":
                self.fail(f"Studio render failed: {status.get('error')}")
            time.sleep(0.25)
        self.fail(f"Studio render {render_id} timed out")

    def test_full_reference_to_720p_download_pipeline(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/studio/providers", headers=self.headers).status_code, 200)

        inspected = self.client.post(
            "/api/v1/studio/reference-videos/inspect",
            headers=self.headers,
            files={"file": ("reference.mp4", self.reference.read_bytes(), "video/mp4")},
        )
        self.assertEqual(inspected.status_code, 201, inspected.text)
        reference_id = inspected.json()["media_id"]
        self.assertGreater(inspected.json()["duration_seconds"], 0)

        analysis_response = self.client.post(
            f"/api/v1/studio/reference-videos/{reference_id}/analyze",
            headers=self.headers,
        )
        self.assertEqual(analysis_response.status_code, 200, analysis_response.text)
        analysis = analysis_response.json()
        self.assertTrue(analysis["frames"])
        frame = analysis["frames"][0]

        studio_routes.init_studio_db()
        image_id = "e" * 32
        image_name = image_id + ".png"
        image_dest = studio_routes._studio_output_dir() / image_name
        shutil.copyfile(self.character, image_dest)
        with studio_routes._connect() as db:
            db.execute(
                """INSERT INTO studio_media
                (id, filename, stored_name, media_type, content_type, size_bytes,
                 source_prompt_id, created_at)
                VALUES (?, ?, ?, 'image', 'image/png', ?, 'e2e-test', '2026-11-16T00:00:00Z')""",
                (image_id, "character.png", image_name, image_dest.stat().st_size),
            )
            db.commit()

        character_response = self.client.post(
            "/api/v1/studio/characters",
            headers=self.headers,
            json={
                "name": "E2E Character",
                "identity": "A fictional test character used only for pipeline validation.",
                "appearance": "Consistent silhouette and dark clothing.",
                "wardrobe": "Simple dark outfit.",
                "continuity_rules": ["Preserve the same character reference in every shot."],
                "reference_media_ids": [image_id],
            },
        )
        self.assertEqual(character_response.status_code, 201, character_response.text)
        character_id = character_response.json()["character_id"]

        shot_payload = {
            "shots": [{
                "analysis_id": analysis["analysis_id"],
                "frame_filename": frame["filename"],
                "timestamp_seconds": 0,
                "title": "Opening shot",
                "duration_seconds": 2.0,
                "camera_direction": "Slow zoom in",
                "visual_notes": "Synthetic acceptance-test frame.",
                "generation_prompt": "Cinematic opening shot for pipeline test.",
                "character_id": character_id,
            }]
        }
        saved = self.client.post(
            f"/api/v1/studio/reference-videos/{reference_id}/shot-map",
            headers=self.headers, json=shot_payload,
        )
        self.assertEqual(saved.status_code, 201, saved.text)
        map_id = saved.json()["map_id"]

        prompts = self.client.post(
            f"/api/v1/studio/reference-videos/shot-maps/{map_id}/build-prompts",
            headers=self.headers,
        )
        self.assertEqual(prompts.status_code, 200, prompts.text)
        self.assertEqual(prompts.json()["prompt_count"], 1)
        self.assertIn("A fictional test character", prompts.text)

        preview = self.client.post(
            f"/api/v1/studio/reference-videos/shot-maps/{map_id}/shots/1/preview",
            headers=self.headers,
            json={"duration_seconds": 1.0, "width": 360, "height": 640, "crf": 26},
        )
        self.assertEqual(preview.status_code, 202, preview.text)
        preview_status = self._wait_for_render(preview.json()["render_id"])
        preview_file = self.client.get(
            preview_status["output_url"], headers=self.headers
        )
        self.assertEqual(preview_file.status_code, 200)
        self.assertTrue(preview_file.content.startswith(b"\x00\x00\x00") or len(preview_file.content) > 1000)

        final = self.client.post(
            f"/api/v1/studio/reference-videos/shot-maps/{map_id}/render",
            headers=self.headers,
            json={"width": 720, "height": 1280, "preset": "veryfast", "crf": 24},
        )
        self.assertEqual(final.status_code, 202, final.text)
        final_status = self._wait_for_render(final.json()["render_id"])
        output = self.client.get(final_status["output_url"], headers=self.headers)
        self.assertEqual(output.status_code, 200)
        self.assertGreater(len(output.content), 1000)

        downloaded = self.root / "final.mp4"
        downloaded.write_bytes(output.content)
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,format_name:stream=codec_type,codec_name,width,height",
            "-of", "json", str(downloaded),
        ], capture_output=True, text=True, check=True, timeout=30)
        metadata = json.loads(probe.stdout)
        video = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
        self.assertEqual((video["width"], video["height"]), (720, 1280))
        self.assertEqual(video["codec_name"], "h264")
        self.assertGreater(float(metadata["format"]["duration"]), 0)
        print("PASS: reference upload → frame analysis → character bible → prompts → shot preview → 720p render → MP4 download")


if __name__ == "__main__":
    unittest.main()
