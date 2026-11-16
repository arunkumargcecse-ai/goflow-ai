# Run goflow.ai in GitHub Codespaces

This setup provisions a browser-based development environment for the existing goflow.ai repository. It is intended for development, demos and testing—not 24/7 production hosting.

## Start

1. Open the repository on GitHub.
2. Select **Code → Codespaces → Create codespace** and choose the `feat/codespaces-cloud-dev-environment` branch (or `main` after this change is merged).
3. Wait for the Codespace to finish creating. The post-create script installs FFmpeg and backend requirements into an isolated `.venv` Python environment. The startup script also repairs a missing/incomplete environment automatically.
4. The post-start script launches:
   - static Creator Studio at port 3000
   - FastAPI at port 8000
5. In the Codespaces **Ports** panel, open port 3000. Keep both forwarded ports set to **Private**.
6. Copy the forwarded HTTPS URL for port 8000 (the hostname ending in `-8000.app.github.dev`). In Creator Studio, paste it into **Backend API URL**.
7. Copy the API key printed by the post-start script and enter it in the API key field. If you need to retrieve it later, run `cat ~/.goflow/codespaces-api-key` in the Codespaces terminal.

## Data and lifecycle

- Application data is written to `$CODESPACE_VOLUMES/data` when the platform exposes a persistent volume, otherwise to `~/.goflow/data` in the Codespace home directory.
- Codespaces can stop when idle and have account-specific free quotas. They are not an always-on server; do not rely on them as the only copy of important media.
- Keep the forwarded ports private. Do not share the API key or expose the API publicly.
- The API key is generated inside the Codespace and is not committed to Git.
- Recreating or deleting a Codespace can remove local data. Download important renders and keep independent backups.

## Scope and limitations

- FFmpeg-based editing, reference frame extraction, shot-map previews and 720p CPU rendering can run, subject to Codespaces CPU and storage limits.
- Heavy diffusion/video models such as Wan 2.2 Animate 14B are not provided by this environment and should not be expected to run.
- This is a temporary development environment. Permanent public hosting still requires a separately provisioned host and secure deployment configuration.


## Automatic Creator Studio connection

When Creator Studio is opened from the forwarded Codespaces port `3000`, the UI automatically derives the matching port `8000` HTTPS URL. In **Quality & tools → Backend connection**, paste the API key printed by `cat ~/.goflow/codespaces-api-key`, then use **Check API health**. The key remains in the current browser tab only; it is not saved in project data. If you are not using the Codespaces port 3000 URL, enter the backend HTTPS URL manually.
