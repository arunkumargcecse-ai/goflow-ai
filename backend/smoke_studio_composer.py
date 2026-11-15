"""Real FFmpeg acceptance test for generated Studio asset composition."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from studio_composer import compose_video


def main() -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("FFmpeg and ffprobe are required for this acceptance test.")
    with tempfile.TemporaryDirectory(prefix="goflow-composer-") as temp:
        root = Path(temp)
        image = root / "still.png"
        video = root / "motion.mp4"
        audio = root / "bed.wav"
        output = root / "final.mp4"
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "color=c=navy:s=320x240", "-frames:v", "1", str(image)],
                       check=True, timeout=30)
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "testsrc=size=320x240:rate=24:duration=2", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", str(video)], check=True, timeout=30)
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "sine=frequency=440:duration=4", str(audio)], check=True, timeout=30)
        result = compose_video([
            {"path": image, "media_type": "image", "duration": 1.2},
            {"path": video, "media_type": "video", "duration": 1.5, "source_in": 0.25},
        ], audio, output, width=360, height=640, preset="veryfast", crf=23)
        probe = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                                "format=duration:stream=width,height", "-of", "json", str(output)],
                               capture_output=True, text=True, check=True, timeout=30)
        metadata = json.loads(probe.stdout)
        duration = float(metadata["format"]["duration"])
        video_stream = next(s for s in metadata["streams"] if "width" in s)
        assert 2.4 <= duration <= 2.9, duration
        assert video_stream["width"] == 360 and video_stream["height"] == 640
        assert result["size_bytes"] > 0
        print(f"PASS: still + video + audio composition, portrait MP4 ({duration:.2f}s, 360x640)")


if __name__ == "__main__":
    main()
