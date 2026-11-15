"""Local reference-video metadata inspection using ffprobe only.

This is analysis/ingestion support, not motion transfer or video generation.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


class ReferenceVideoError(ValueError):
    pass


def inspect_reference_video(data: bytes, *, max_duration: float = 180.0) -> dict:
    if not data or len(data) > 100 * 1024 * 1024:
        raise ReferenceVideoError("Reference video must be between 1 byte and 100 MB.")
    executable = shutil.which("ffprobe")
    if not executable:
        raise RuntimeError("ffprobe is not installed. Install FFmpeg to inspect reference videos.")
    with tempfile.TemporaryDirectory(prefix="goflow-reference-") as temp_dir:
        path = Path(temp_dir) / "reference-video"
        path.write_bytes(data)
        command = [
            executable, "-v", "error", "-show_streams", "-show_format",
            "-of", "json", str(path),
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=True)
            metadata = json.loads(completed.stdout)
        except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
            raise ReferenceVideoError("The uploaded file is not a readable video.") from exc
    streams = metadata.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if not video:
        raise ReferenceVideoError("The uploaded file contains no video stream.")
    try:
        width, height = int(video["width"]), int(video["height"])
        duration = float(metadata.get("format", {}).get("duration") or video.get("duration"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ReferenceVideoError("Video metadata is incomplete or invalid.") from exc
    if width < 2 or height < 2 or width > 8192 or height > 8192:
        raise ReferenceVideoError("Video dimensions are outside the supported 2–8192 pixel range.")
    if not 0 < duration <= max_duration:
        raise ReferenceVideoError(f"Reference video must be longer than 0 and no longer than {int(max_duration)} seconds.")
    rate = str(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1")
    try:
        numerator, denominator = rate.split("/", 1)
        fps = round(float(numerator) / float(denominator), 3) if float(denominator) else 0.0
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    return {
        "duration_seconds": round(duration, 3),
        "width": width,
        "height": height,
        "fps": fps,
        "codec": str(video.get("codec_name", "unknown"))[:40],
        "pixel_format": str(video.get("pix_fmt", "unknown"))[:40],
        "orientation": "portrait" if height > width else "landscape" if width > height else "square",
        "aspect_ratio": f"{width}:{height}",
        "recommended_analysis": {
            "sample_interval_seconds": max(1, round(duration / 12, 2)),
            "max_sample_frames": min(12, max(1, int(duration))),
            "purpose": "Use sampled frames to plan shots and composition before motion-transfer generation.",
        },
        "motion_transfer_generated": False,
    }
