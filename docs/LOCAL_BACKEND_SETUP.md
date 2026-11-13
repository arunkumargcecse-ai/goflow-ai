# Run the goflow.ai backend locally (free)

This runs the FastAPI + FFmpeg backend on your own Windows laptop using Docker Desktop. It does not create a cloud service or incur hosting charges. Docker Desktop installation and local video processing use your laptop's resources.

## Requirements

- Windows 11 (or macOS/Linux)
- Docker Desktop with Docker Compose v2
- Internet access for the first image build; video processing itself runs locally
- Enough free disk space for source uploads and rendered MP4 files

## First-time setup (Windows PowerShell)

1. Install Docker Desktop from the official Docker website and start it. If prompted, enable the WSL 2 backend and restart Windows.
2. Clone this repository and open PowerShell in the repository folder.
3. Create your private environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

4. Generate a random key and copy it into the `GOFLOW_API_KEY` value in `.env`:

   ```powershell
   [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
   ```

   Keep this key private. Do not commit `.env` or paste the key into chat.

5. Build and start the backend:

   ```powershell
   docker compose up -d --build
   ```

6. Confirm the backend is healthy:

   ```powershell
   Invoke-RestMethod http://localhost:10000/health
   Invoke-RestMethod http://localhost:10000/api/v1/capabilities
   ```

7. Open the goflow.ai Studio website. In **Quality & tools**, set the Backend URL to `http://localhost:10000`, enter the same API key from your private `.env` file in the Studio's Media API key field, and run the API health check.

8. Upload a short, non-sensitive test video, map/edit clip ranges, render, and verify the resulting MP4 plays and downloads.

## Start, stop and update

- Start: `docker compose up -d`
- Stop: `docker compose down`
- View logs: `docker compose logs -f goflow-api`
- Rebuild after code changes: `docker compose up -d --build`

The named Docker volume `goflow_ai_data` stores uploads, rendered outputs and the SQLite database across container restarts and rebuilds. `docker compose down -v` deletes that volume and all stored media; do not run it unless you intentionally want to erase the local media store.

## Security and limitations

- The API port is bound to `127.0.0.1`, not exposed to your LAN.
- The browser Studio can call localhost from its configured origin. Do not change the bind address to `0.0.0.0` or expose this API publicly without adding proper authentication, rate limits and access controls.
- The API key is stored only in the ignored local `.env` file and must also be entered into the Studio UI for media operations.
- The current job runner uses FastAPI BackgroundTasks, not a durable worker queue. Avoid closing Docker or shutting down the laptop during a render.
- This is a local single-user setup. The browser-based Studio must be open on the same computer that runs Docker.
- Local rendering is limited by laptop CPU, RAM, thermal capacity and free disk space. Start with a short 10–20 second test clip.
- Docker's first build downloads the Python base image and dependencies. No paid cloud resources are provisioned.
