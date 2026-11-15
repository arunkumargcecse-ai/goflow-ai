"""Local reference-video frame sampling and lightweight cut detection.

Uses only FFmpeg/ffprobe; it does not estimate poses or transfer motion.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


class ReferenceAnalysisError(ValueError):
    pass


def analyze_reference_video(video_path: Path, output_dir: Path, *, max_frames: int = 12) -> dict:
    if not 1 <= max_frames <= 12:
        raise ReferenceAnalysisError("max_frames must be between 1 and 12.")
    video_path = Path(video_path).resolve()
    if not video_path.is_file():
        raise ReferenceAnalysisError("Reference video file was not found.")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not installed. Install FFmpeg to extract reference frames.")

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    # Detect candidate hard cuts with FFmpeg's built-in scene score.
    cut_command = [
        ffmpeg, "-hide_banner", "-i", str(video_path), "-vf",
        "select='gt(scene,0.28)',showinfo", "-an", "-f", "null", "-"
    ]
    try:
        result = subprocess.run(cut_command, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired as exc:
        raise ReferenceAnalysisError("Reference scene scan exceeded 90 seconds.") from exc
    if result.returncode != 0:
        raise ReferenceAnalysisError("FFmpeg could not scan the reference video.")
    cut_times = []
    for match in re.finditer(r"pts_time:([0-9]+(?:\.[0-9]+)?)", result.stderr):
        value = float(match.group(1))
        if value >= 0:
            cut_times.append(round(value, 3))

    # Read duration using ffprobe; avoid relying on uploaded metadata from the client.
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is not installed. Install FFmpeg to inspect reference videos.")
    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True, timeout=30, check=True,
    )
    try:
        duration = float(probe.stdout.strip())
    except ValueError as exc:
        raise ReferenceAnalysisError("Reference video duration could not be read.") from exc
    if not 0 < duration <= 180:
        raise ReferenceAnalysisError("Reference video must be no longer than 180 seconds.")

    uniform_count = min(max_frames, max(1, round(duration / 2.5)))
    uniform = [round((i + 0.5) * duration / uniform_count, 3) for i in range(uniform_count)]
    # Prioritize cut-adjacent frames, then fill remaining slots with evenly spaced samples.
    candidates = sorted(set(uniform + [t for t in cut_times if t < duration]))
    if len(candidates) > max_frames:
        selected = []
        for i in range(max_frames):
            selected.append(candidates[round(i * (len(candidates) - 1) / max(1, max_frames - 1))])
        candidates = sorted(set(selected))
    frames = []
    for index, timestamp in enumerate(candidates, start=1):
        filename = f"frame-{index:02d}.jpg"
        destination = output_dir / filename
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", str(timestamp),
            "-i", str(video_path), "-frames:v", "1", "-vf", "scale=480:-2",
            "-q:v", "4", "-y", str(destination),
        ]
        try:
            subprocess.run(command, capture_output=True, text=True, timeout=30, check=True)
        except (subprocess.SubprocessError, OSError) as exc:
            raise ReferenceAnalysisError(f"Could not extract reference frame at {timestamp:.2f}s.") from exc
        if not destination.is_file() or destination.stat().st_size == 0:
            raise ReferenceAnalysisError(f"FFmpeg produced an empty frame at {timestamp:.2f}s.")
        frames.append({"index": index, "timestamp_seconds": timestamp, "filename": filename,
                       "shot_id": index, "source": "scene_cut" if any(abs(timestamp-t) < .02 for t in cut_times) else "sample"})
    return {
        "duration_seconds": round(duration, 3),
        "scene_cut_count": len(cut_times),
        "sampled_frame_count": len(frames),
        "frames": frames,
        "analysis_method": "ffmpeg_scene_score_and_uniform_sampling",
        "pose_estimation": False,
        "camera_motion_estimation": False,
        "motion_transfer_generated": False,
    }
