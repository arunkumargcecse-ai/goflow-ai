# Windows local setup

This guide runs the existing goflow.ai FastAPI backend and Creator Studio on Windows 10/11. It is intended for a local, single-user development setup.

## Requirements

- Windows 10 or 11, 64-bit.
- Python 3.11 or 3.12 (64-bit), with the Python Launcher enabled.
- Git, or download the repository ZIP and extract it.
- FFmpeg **and** ffprobe on PATH for video rendering, reference-frame extraction and media probing.
- Internet access for the one-time Python package installation.

No paid API is used by these startup scripts. They do not download AI model weights. Local ComfyUI, Piper voice models and eSpeak are optional and must be installed/configured separately.

## First run

1. Download/clone the repository and extract it to a folder such as `C:\goflow-ai`.
2. Install Python 3.11 or 3.12. Enable **Add Python to PATH** and the Python Launcher.
3. Install FFmpeg and add its `bin` folder to PATH. Open a new terminal and confirm `ffmpeg -version` and `ffprobe -version` work.
4. Double-click `setup_goflow.bat`. It creates `.venv`, installs `backend/requirements.txt`, and generates a random local API key in the ignored `.env` file.
5. Double-click `start_goflow.bat`. Keep its console window open. It starts Uvicorn bound to loopback only (`127.0.0.1`) and opens the Creator Studio HTML file.
6. In Creator Studio's **Backend URL** field, replace the hosted URL with `http://127.0.0.1:8000`.
7. In **Media API key**, paste the key printed in the start window. Use **Check API health** to confirm the backend is reachable.

The local API is intentionally bound to `127.0.0.1`; it is not exposed to your Wi-Fi/LAN. Do not change the bind address or share the generated key.

## What works locally

- Story and storyboard planning, reference-video inspection and shot-map editing.
- FFmpeg-based per-shot previews, full-sequence draft previews and 720p MP4 composition.
- Local audio-track mixing.
- Local Tamil voiceover only when Piper with a configured Tamil ONNX voice model or eSpeak with a Tamil voice is installed and ready.
- Local ComfyUI workflows only when ComfyUI, compatible models and custom nodes are separately installed and configured.

## Important hardware and generation limits

The Samsung Galaxy Book4 configuration with Intel Core i5-1335U, 16 GB RAM and Intel Iris Xe integrated graphics is suitable for the app, editing, FFmpeg previews and modest 720p composition (render time depends heavily on source length and effects). It is **not** suitable for running the 14B Wan 2.2 Animate model locally. The local shot-map renderer animates still images with FFmpeg pan/zoom; it does not transfer real body/face motion from the reference video.

Image/video generation providers default to offline/mock mode. A healthy API response does not mean a generative image or video model is installed.

## Troubleshooting

- **Python not found:** install Python 3.11/3.12 x64 and enable the Python Launcher.
- **FFmpeg not installed:** install a Windows FFmpeg build, add its `bin` directory to PATH, then reopen the setup/start windows.
- **Port 8000 already in use:** close the other local service or change the port in `start_goflow.bat` and the Creator Studio Backend URL to the same value.
- **API health fails:** keep the server console open, verify the Backend URL is exactly `http://127.0.0.1:8000`, and re-enter the key printed by the server launcher.
- **Tamil voice unavailable:** check `/api/v1/studio/providers`; install/configure a local engine and Tamil voice. No cloud fallback is performed.

## Data and security

Local databases, uploads, renders, virtual environments and `.env` are stored locally and ignored by Git. Back up your `backend/data` folder if you need to retain projects and media. Never commit or share `.env`.
