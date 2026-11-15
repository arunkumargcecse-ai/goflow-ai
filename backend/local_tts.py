"""Offline local text-to-speech adapters for goflow.ai.

Supports Piper when a local voice model is configured, or eSpeak NG/eSpeak when
the requested voice is installed. No network calls or paid APIs are used.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _voice_exists(executable: str, voice: str) -> bool:
    try:
        result = subprocess.run(
            [executable, "--voices"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return result.returncode == 0 and voice.lower() in result.stdout.lower()
    except (OSError, subprocess.TimeoutExpired):
        return False


def available_engines() -> dict:
    piper = shutil.which("piper")
    model = os.getenv("GOFLOW_PIPER_MODEL", "").strip()
    piper_ready = bool(piper and model and Path(model).is_file())
    espeak = shutil.which("espeak-ng") or shutil.which("espeak")
    espeak_ready = bool(espeak and _voice_exists(espeak, "ta"))
    return {
        "piper": {"installed": bool(piper), "model_configured": bool(model),
                  "model_exists": bool(model and Path(model).is_file()), "ready": piper_ready},
        "espeak": {"installed": bool(espeak), "tamil_voice_available": espeak_ready, "ready": espeak_ready},
    }


def synthesize_speech(
    text: str,
    output_path: Path,
    *,
    engine: str = "auto",
    voice: str = "ta",
    speed: int = 145,
) -> dict:
    """Render text to a WAV file using a locally installed speech engine."""
    text = text.strip()
    if not text or len(text) > 5000:
        raise ValueError("Narration text must contain 1 to 5000 characters.")
    if engine not in {"auto", "piper", "espeak"}:
        raise ValueError("Engine must be auto, piper, or espeak.")
    if not voice or len(voice) > 80 or any(ch in voice for ch in "\r\n"):
        raise ValueError("Invalid voice identifier.")
    if speed < 80 or speed > 250:
        raise ValueError("Speech speed must be between 80 and 250 words per minute.")

    status = available_engines()
    selected = engine
    if selected == "auto":
        selected = "piper" if status["piper"]["ready"] else "espeak"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)

    if selected == "piper":
        executable = shutil.which("piper")
        model = os.getenv("GOFLOW_PIPER_MODEL", "").strip()
        if not executable or not model or not Path(model).is_file():
            raise RuntimeError("Piper is not ready. Install piper and configure GOFLOW_PIPER_MODEL to a local voice .onnx file.")
        command = [executable, "--model", model, "--output_file", str(output_path)]
        provider_voice = Path(model).name
    else:
        executable = shutil.which("espeak-ng") or shutil.which("espeak")
        if not executable:
            raise RuntimeError("No local TTS engine is installed. Install eSpeak NG or Piper with a local voice model.")
        if not _voice_exists(executable, voice):
            raise RuntimeError(f"The local eSpeak installation does not include the '{voice}' voice. Install a Tamil voice or configure Piper.")
        command = [executable, "-v", voice, "-s", str(speed), "-w", str(output_path), "--stdin"]
        provider_voice = voice

    try:
        result = subprocess.run(
            command, input=text, capture_output=True, text=True,
            timeout=180, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("Local speech synthesis exceeded the 180-second limit.") from exc
    if result.returncode != 0 or not output_path.is_file() or output_path.stat().st_size < 44:
        output_path.unlink(missing_ok=True)
        message = (result.stderr or result.stdout or "TTS engine produced no valid WAV output").strip()
        raise RuntimeError(message[-1200:])
    with output_path.open("rb") as audio:
        if audio.read(4) != b"RIFF":
            output_path.unlink(missing_ok=True)
            raise RuntimeError("The local TTS engine did not produce a WAV audio file.")
    return {
        "engine": selected,
        "voice": provider_voice,
        "format": "wav",
        "size_bytes": output_path.stat().st_size,
        "characters": len(text),
    }
