import tempfile
import unittest
from pathlib import Path

import main


class MediaEngineFoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        main.DB_PATH = Path(self.temp_dir.name) / "test.sqlite3"
        main.init_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_initializes_and_persists_job_records(self):
        now = main.utc_now()
        with main.connect_db() as db:
            db.execute(
                "INSERT INTO media (id, filename, stored_name, size_bytes, created_at) VALUES (?, ?, ?, ?, ?)",
                ("media-1", "source.mp4", "source.mp4", 123, now),
            )
            db.execute(
                "INSERT INTO jobs (id, media_id, status, progress, request_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("job-1", "media-1", "queued", 0, '{"media_id":"media-1"}', now, now),
            )
            db.commit()
        self.assertEqual(main.get_media("media-1")["filename"], "source.mp4")
        job = main.get_job("job-1")
        self.assertEqual(job["status"], "queued")
        self.assertEqual(job["request"]["media_id"], "media-1")

    def test_render_request_applies_safe_defaults_and_bounds(self):
        request = main.RenderRequest(media_id="media-1")
        self.assertEqual(request.output_width, 1080)
        self.assertEqual(request.output_height, 1920)
        self.assertEqual(request.preset, "balanced")
        with self.assertRaises(Exception):
            main.RenderRequest(media_id="media-1", output_width=10000)

    def test_capabilities_report_real_local_tool_presence(self):
        capabilities = main.capabilities()
        self.assertIn(capabilities["ffmpeg_rendering"], {"available", "not_installed"})
        self.assertIn(capabilities["ffprobe"], {"available", "not_installed"})
        self.assertEqual(capabilities["transcription"], "not_connected")


if __name__ == "__main__":
    unittest.main()
