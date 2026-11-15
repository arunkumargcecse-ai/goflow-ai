"""FFmpeg composition for storyboard shots backed by imported Studio media."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def compose_video(
    clips: list[dict],
    audio_path: Path | None,
    output_path: Path,
    *,
    width: int = 1080,
    height: int = 1920,
    preset: str = "slow",
    crf: int = 18,
) -> dict:
    """Compose image/video clips in order, optionally laying one audio track underneath."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("FFmpeg and ffprobe must be installed on the local worker.")
    if not clips:
        raise ValueError("At least one storyboard clip is required.")
    if width < 320 or width > 3840 or height < 320 or height > 3840:
        raise ValueError("Output dimensions must be between 320 and 3840 pixels.")
    if preset not in {"veryfast", "medium", "slow", "veryslow"}:
        raise ValueError("Unsupported FFmpeg preset.")

    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    filters: list[str] = []
    concat_labels: list[str] = []
    cursor = 0.0
    for index, clip in enumerate(clips):
        path = Path(clip["path"]).resolve()
        duration = float(clip["duration"])
        if duration <= 0 or duration > 600:
            raise ValueError("Each shot duration must be greater than 0 and at most 600 seconds.")
        media_type = clip["media_type"]
        if media_type == "image":
            command += ["-loop", "1", "-t", str(duration), "-i", str(path)]
            video_filter = f"[{index}:v]trim=duration={duration},setpts=PTS-STARTPTS"
        elif media_type == "video":
            start = float(clip.get("source_in") or 0)
            end = clip.get("source_out")
            if end is not None and float(end) <= start:
                raise ValueError("Video source-out must be greater than source-in.")
            command += ["-i", str(path)]
            if end is not None and float(end) - start < duration:
                raise ValueError("Requested shot duration exceeds the selected video source range.")
            video_filter = f"[{index}:v]trim=start={start}:duration={duration},setpts=PTS-STARTPTS"
        else:
            raise ValueError("Storyboard media must be an image or video.")
        video_filter += (
            f",scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[v{index}]"
        )
        filters.append(video_filter)
        concat_labels.append(f"[v{index}]")
        cursor += duration

    total_duration = sum(float(clip["duration"]) for clip in clips)
    filters.append("".join(concat_labels) + f"concat=n={len(clips)}:v=1:a=0[vout]")
    if audio_path:
        audio_index = len(clips)
        command += ["-stream_loop", "-1", "-i", str(Path(audio_path).resolve())]
        filters.append(f"[{audio_index}:a]atrim=duration={total_duration},asetpts=PTS-STARTPTS[aout]")
    command += ["-filter_complex", ";".join(filters), "-map", "[vout]"]
    if audio_path:
        command += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    else:
        command += ["-an"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command += [
        "-t", str(total_duration), "-c:v", "libx264", "-preset", preset,
        "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=4 * 60 * 60)
    if result.returncode:
        output_path.unlink(missing_ok=True)
        raise RuntimeError((result.stderr or "FFmpeg composition failed")[-3000:])
    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=width,height",
         "-of", "json", str(output_path)],
        capture_output=True, text=True, check=True, timeout=60,
    )
    import json
    metadata = json.loads(probe.stdout)
    actual_duration = float(metadata.get("format", {}).get("duration") or 0)
    if actual_duration <= 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("FFprobe could not verify the rendered output duration.")
    return {"duration_seconds": actual_duration, "width": width, "height": height, "size_bytes": output_path.stat().st_size}
