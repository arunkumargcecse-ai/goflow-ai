"""Exercise the real local API upload -> multi-clip FFmpeg render -> download path.

Run from the backend directory after installing requirements and FFmpeg:
    python smoke_render.py
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def request(url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read()


def main() -> None:
    ffmpeg = os.environ.get("FFMPEG", "ffmpeg")
    ffprobe = os.environ.get("FFPROBE", "ffprobe")
    with tempfile.TemporaryDirectory(prefix="goflow-e2e-") as temp:
        root = Path(temp)
        source = root / "source.mp4"
        subprocess.run(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=3:r=24",
                "-f", "lavfi", "-i", "sine=frequency=880:duration=3",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", str(source),
            ],
            check=True, timeout=30,
        )

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        api_key = uuid.uuid4().hex + uuid.uuid4().hex
        env = os.environ.copy()
        env.update(
            GOFLOW_API_KEY=api_key,
            GOFLOW_DATA_DIR=str(root / "data"),
            GOFLOW_CORS_ORIGINS="http://127.0.0.1",
        )
        server = subprocess.Popen(
            [
                os.environ.get("PYTHON", "python"), "-m", "uvicorn",
                "main:app", "--host", "127.0.0.1", "--port", str(port),
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(40):
                if server.poll() is not None:
                    raise RuntimeError("API server exited before becoming healthy")
                try:
                    status, _, body = request(base + "/health")
                    if status == 200:
                        break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.5)
            else:
                raise RuntimeError("API did not become healthy within 20 seconds")

            status, _, _ = request(base + "/api/v1/media/upload", data=b"")
            if status != 401:
                raise AssertionError(f"Unauthenticated upload expected 401, got {status}")

            boundary = "----goflow-" + uuid.uuid4().hex
            payload = source.read_bytes()
            multipart = (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="file"; filename="source.mp4"\r\n'
                "Content-Type: video/mp4\r\n\r\n"
            ).encode() + payload + f"\r\n--{boundary}--\r\n".encode()
            status, _, body = request(
                base + "/api/v1/media/upload",
                data=multipart,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "X-Goflow-Key": api_key,
                },
            )
            if status != 200:
                raise AssertionError(f"Upload failed ({status}): {body.decode(errors='replace')}")
            media_id = json.loads(body)["id"]

            render_body = json.dumps({
                "media_id": media_id,
                "clips": [
                    {"start_seconds": 0.0, "end_seconds": 1.0},
                    {"start_seconds": 1.5, "end_seconds": 2.5},
                ],
                "output_width": 320,
                "output_height": 320,
                "preset": "fast",
            }).encode()
            status, _, body = request(
                base + "/api/v1/jobs/render",
                data=render_body,
                headers={"Content-Type": "application/json", "X-Goflow-Key": api_key},
            )
            if status != 202:
                raise AssertionError(f"Render submission failed ({status}): {body.decode(errors='replace')}")
            job_id = json.loads(body)["job_id"]

            for _ in range(120):
                status, _, body = request(base + f"/api/v1/jobs/{job_id}")
                if status != 200:
                    raise AssertionError(f"Job status failed ({status})")
                job = json.loads(body)
                if job["status"] == "completed":
                    break
                if job["status"] == "failed":
                    raise AssertionError(f"FFmpeg render failed: {job.get('error')}")
                time.sleep(0.5)
            else:
                raise TimeoutError("Render did not finish within 60 seconds")

            status, headers, rendered = request(
                base + f"/api/v1/jobs/{job_id}/output",
                headers={"X-Goflow-Key": api_key},
            )
            if status != 200 or not rendered.startswith(b"\x00\x00\x00"):
                # MP4 files commonly begin with an ftyp box at byte offset 4.
                if status != 200 or rendered[4:8] != b"ftyp":
                    raise AssertionError(f"Output download failed or is not MP4 (HTTP {status})")
            output = root / "rendered.mp4"
            output.write_bytes(rendered)
            probe = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "json", str(output)],
                capture_output=True, text=True, check=True, timeout=15,
            )
            duration = float(json.loads(probe.stdout)["format"]["duration"])
            if not 1.5 <= duration <= 2.5:
                raise AssertionError(f"Unexpected rendered duration: {duration}")
            print(f"PASS: upload, API-key enforcement, two-clip FFmpeg render and MP4 download ({duration:.2f}s)")
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


if __name__ == "__main__":
    main()
