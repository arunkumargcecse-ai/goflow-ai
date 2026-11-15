import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from studio_composer import MOTION_PRESETS, _image_motion_filter, compose_video


class ImageMotionFilterTests(unittest.TestCase):
    def test_all_motion_presets_are_supported(self):
        for preset in MOTION_PRESETS:
            with self.subTest(preset=preset):
                value = _image_motion_filter(0, 2.0, 360, 640, preset)
                self.assertIn("[0:v]", value)
                self.assertIn("scale=360:640", value)
                if preset == "static":
                    self.assertNotIn("zoompan", value)
                else:
                    self.assertIn("zoompan", value)

    def test_invalid_motion_preset_is_rejected(self):
        with self.assertRaises(ValueError):
            _image_motion_filter(0, 2.0, 360, 640, "run-arbitrary-filter")


class ComposeVideoMotionTests(unittest.TestCase):
    @patch("studio_composer.subprocess.run")
    @patch("studio_composer.shutil.which", side_effect=lambda name: f"/usr/bin/{name}")
    def test_image_scene_renders_with_zoompan_and_is_probed(self, _which, run):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "scene.mp4"

            def fake_run(command, **kwargs):
                if command[0].endswith("ffmpeg"):
                    output.write_bytes(b"fake-mp4")
                    return SimpleNamespace(returncode=0, stderr="", stdout="")
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps({"format": {"duration": "2.0"}, "streams": [{"width": 360, "height": 640}]}),
                    stderr="",
                )

            run.side_effect = fake_run
            result = compose_video(
                [{"path": Path(folder) / "still.png", "media_type": "image", "duration": 2.0, "motion": "zoom_in"}],
                None, output, width=360, height=640, preset="veryfast",
            )
            command = run.call_args_list[0].args[0]
            self.assertIn("zoompan", command[command.index("-filter_complex") + 1])
            self.assertEqual(result["motion_presets"], ["zoom_in"])
            self.assertEqual(result["duration_seconds"], 2.0)

    @patch("studio_composer.shutil.which", side_effect=lambda name: f"/usr/bin/{name}")
    def test_invalid_motion_is_rejected_before_ffmpeg_runs(self, _which):
        with tempfile.TemporaryDirectory() as folder:
            with patch("studio_composer.subprocess.run") as run:
                with self.assertRaises(ValueError):
                    compose_video(
                        [{"path": Path(folder) / "still.png", "media_type": "image",
                          "duration": 2.0, "motion": "arbitrary"}],
                        None, Path(folder) / "out.mp4", width=360, height=640,
                    )
                run.assert_not_called()

    @patch("studio_composer.subprocess.run")
    @patch("studio_composer.shutil.which", side_effect=lambda name: f"/usr/bin/{name}")
    def test_multiple_audio_tracks_are_delayed_and_mixed(self, _which, run):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "mixed.mp4"

            def fake_run(command, **kwargs):
                if command[0].endswith("ffmpeg"):
                    output.write_bytes(b"fake-mp4")
                    return SimpleNamespace(returncode=0, stderr="", stdout="")
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps({"format": {"duration": "4.0"}, "streams": [{"width": 360, "height": 640}]}),
                    stderr="",
                )

            run.side_effect = fake_run
            result = compose_video(
                [{"path": Path(folder) / "still.png", "media_type": "image", "duration": 4.0, "motion": "static"}],
                None, output, width=360, height=640, preset="veryfast",
                audio_tracks=[
                    {"path": Path(folder) / "voice.wav", "start_seconds": 0.5, "volume": 1.0, "loop": False},
                    {"path": Path(folder) / "music.mp3", "start_seconds": 0, "volume": 0.2, "loop": True},
                ],
            )
            command = run.call_args_list[0].args[0]
            graph = command[command.index("-filter_complex") + 1]
            self.assertIn("adelay=500|500", graph)
            self.assertIn("volume=0.2", graph)
            self.assertIn("amix=inputs=2", graph)
            self.assertEqual(result["audio_track_count"], 2)

    def test_audio_track_bounds_are_validated_before_render(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("studio_composer.shutil.which", side_effect=lambda name: f"/usr/bin/{name}"):
                with patch("studio_composer.subprocess.run") as run:
                    with self.assertRaises(ValueError):
                        compose_video(
                            [{"path": Path(folder) / "still.png", "media_type": "image", "duration": 2.0}],
                            None, Path(folder) / "out.mp4", width=360, height=640,
                            audio_tracks=[{"path": Path(folder) / "music.mp3", "volume": 3.0}],
                        )
                    run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
