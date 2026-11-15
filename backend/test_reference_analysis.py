import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from reference_analysis import ReferenceAnalysisError, analyze_reference_video


class ReferenceFrameAnalysisTests(unittest.TestCase):
    def test_rejects_invalid_frame_limit(self):
        with self.assertRaises(ReferenceAnalysisError):
            analyze_reference_video(Path("missing.mp4"), Path("out"), max_frames=13)

    def test_rejects_missing_video(self):
        with self.assertRaises(ReferenceAnalysisError):
            analyze_reference_video(Path("missing.mp4"), Path("out"))

    @patch("reference_analysis.subprocess.run")
    @patch("reference_analysis.shutil.which")
    def test_extracts_sampled_frames_and_reports_limits(self, which, run):
        which.side_effect = ["/usr/bin/ffmpeg", "/usr/bin/ffprobe"]
        def invoke(command, **kwargs):
            if command[0].endswith("ffprobe"):
                return Mock(stdout="8.0")
            if "-f" in command and "null" in command:
                return Mock(returncode=0, stderr="[Parsed_showinfo] pts_time:2.0")
            Path(command[-1]).write_bytes(b"jpeg")
            return Mock(returncode=0, stderr="")
        run.side_effect = invoke
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "ref.mp4"
            source.write_bytes(b"video")
            result = analyze_reference_video(source, Path(temp) / "frames", max_frames=4)
            self.assertLessEqual(result["sampled_frame_count"], 4)
            self.assertFalse(result["pose_estimation"])
            self.assertFalse(result["camera_motion_estimation"])
            self.assertFalse(result["motion_transfer_generated"])
            self.assertTrue(all((Path(temp) / "frames" / f["filename"]).is_file() for f in result["frames"]))


if __name__ == "__main__":
    unittest.main()
