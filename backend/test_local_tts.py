import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from local_tts import synthesize_speech


class LocalTtsTests(unittest.TestCase):
    def test_invalid_text_and_speed_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                synthesize_speech("   ", Path(folder) / "voice.wav")
            with self.assertRaises(ValueError):
                synthesize_speech("Vanakkam", Path(folder) / "voice.wav", speed=400)

    @patch("local_tts.available_engines", return_value={
        "piper": {"ready": True}, "espeak": {"ready": False}
    })
    @patch("local_tts.shutil.which", return_value="/usr/bin/piper")
    def test_piper_synthesis_creates_registered_wav(self, _which, _status):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / "ta.onnx"
            model.write_bytes(b"model")
            output = Path(folder) / "voice.wav"

            def fake_run(command, **kwargs):
                output.write_bytes(b"RIFF" + b"\x00" * 48)
                return SimpleNamespace(returncode=0, stderr="", stdout="")

            with patch.dict(os.environ, {"GOFLOW_PIPER_MODEL": str(model)}):
                with patch("local_tts.subprocess.run", side_effect=fake_run):
                    result = synthesize_speech("வணக்கம்", output, engine="piper")
            self.assertEqual(result["engine"], "piper")
            self.assertEqual(result["format"], "wav")
            self.assertEqual(result["characters"], 7)
            self.assertTrue(output.is_file())

    @patch("local_tts.available_engines", return_value={
        "piper": {"ready": False}, "espeak": {"ready": False}
    })
    @patch("local_tts.shutil.which", return_value=None)
    def test_missing_local_engine_fails_without_network_fallback(self, _which, _status):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, "No local TTS engine"):
                synthesize_speech("Vanakkam", Path(folder) / "voice.wav", engine="espeak")


if __name__ == "__main__":
    unittest.main()
