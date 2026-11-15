import json
import unittest
from unittest.mock import patch, Mock

from reference_video import ReferenceVideoError, inspect_reference_video


class ReferenceVideoInspectionTests(unittest.TestCase):
    @patch("reference_video.shutil.which", return_value=None)
    def test_requires_ffprobe(self, _):
        with self.assertRaises(RuntimeError):
            inspect_reference_video(b"video")

    @patch("reference_video.subprocess.run")
    @patch("reference_video.shutil.which", return_value="/usr/bin/ffprobe")
    def test_returns_metadata_without_claiming_motion_transfer(self, _, run):
        run.return_value = Mock(stdout=json.dumps({
            "format": {"duration": "12.5"},
            "streams": [{
                "codec_type": "video", "width": 720, "height": 1280,
                "avg_frame_rate": "30/1", "codec_name": "h264", "pix_fmt": "yuv420p",
            }],
        }))
        result = inspect_reference_video(b"video-bytes")
        self.assertEqual(result["orientation"], "portrait")
        self.assertEqual(result["fps"], 30.0)
        self.assertFalse(result["motion_transfer_generated"])
        self.assertEqual(result["recommended_analysis"]["max_sample_frames"], 12)

    def test_rejects_empty_and_oversized_uploads(self):
        with self.assertRaises(ReferenceVideoError):
            inspect_reference_video(b"")
        with self.assertRaises(ReferenceVideoError):
            inspect_reference_video(b"x" * (100 * 1024 * 1024 + 1))

    @patch("reference_video.subprocess.run")
    @patch("reference_video.shutil.which", return_value="/usr/bin/ffprobe")
    def test_rejects_video_longer_than_three_minutes(self, _, run):
        run.return_value = Mock(stdout=json.dumps({
            "format": {"duration": "181"},
            "streams": [{"codec_type": "video", "width": 1920, "height": 1080}],
        }))
        with self.assertRaises(ReferenceVideoError):
            inspect_reference_video(b"video-bytes")


if __name__ == "__main__":
    unittest.main()
