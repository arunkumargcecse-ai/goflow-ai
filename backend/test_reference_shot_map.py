import unittest
from pydantic import ValidationError

from studio_routes import ReferenceShot, ReferenceShotMapRequest, ShotMapRenderRequest, ShotPreviewRequest, _shot_motion_preset


class ReferenceShotMapModelTests(unittest.TestCase):
    def test_accepts_valid_shot(self):
        shot = ReferenceShot(
            analysis_id="a" * 32,
            frame_filename="frame-01.jpg",
            timestamp_seconds=1.25,
            title="Opening",
        )
        payload = ReferenceShotMapRequest(shots=[shot])
        self.assertEqual(payload.shots[0].title, "Opening")

    def test_rejects_path_traversal_filename(self):
        with self.assertRaises(ValidationError):
            ReferenceShot(
                analysis_id="a" * 32,
                frame_filename="../secret.jpg",
                timestamp_seconds=1,
            )

    def test_shot_map_render_defaults_to_laptop_friendly_720p(self):
        payload = ShotMapRenderRequest()
        self.assertEqual((payload.width, payload.height), (720, 1280))
        self.assertEqual(payload.preset, "veryfast")
        self.assertEqual(payload.crf, 22)

    def test_shot_preview_defaults_to_small_fast_preview(self):
        payload = ShotPreviewRequest()
        self.assertEqual(payload.duration_seconds, 2.5)
        self.assertEqual((payload.width, payload.height), (360, 640))
        self.assertEqual(payload.crf, 25)

    def test_shot_preview_rejects_long_duration_and_large_dimensions(self):
        with self.assertRaises(ValidationError):
            ShotPreviewRequest(duration_seconds=9)
        with self.assertRaises(ValidationError):
            ShotPreviewRequest(width=1080, height=1920)

    def test_camera_direction_maps_to_safe_motion_presets(self):
        self.assertEqual(_shot_motion_preset("Pan left slowly"), "pan_left")
        self.assertEqual(_shot_motion_preset("Camera moves right"), "pan_right")
        self.assertEqual(_shot_motion_preset("Zoom out to wide shot"), "zoom_out")
        self.assertEqual(_shot_motion_preset("Locked static shot"), "static")
        self.assertEqual(_shot_motion_preset("Dolly forward"), "zoom_in")

    def test_rejects_out_of_range_render_dimensions(self):
        with self.assertRaises(ValidationError):
            ShotMapRenderRequest(width=100, height=1280)

    def test_rejects_more_than_twelve_shots(self):
        shots = [
            {"analysis_id": "a" * 32, "frame_filename": f"frame-{i:02}.jpg", "timestamp_seconds": i}
            for i in range(1, 14)
        ]
        with self.assertRaises(ValidationError):
            ReferenceShotMapRequest(shots=shots)


if __name__ == "__main__":
    unittest.main()
