import unittest
from pydantic import ValidationError

from studio_routes import ReferenceShot, ReferenceShotMapRequest


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

    def test_rejects_more_than_twelve_shots(self):
        shots = [
            {"analysis_id": "a" * 32, "frame_filename": f"frame-{i:02}.jpg", "timestamp_seconds": i}
            for i in range(1, 14)
        ]
        with self.assertRaises(ValidationError):
            ReferenceShotMapRequest(shots=shots)


if __name__ == "__main__":
    unittest.main()
