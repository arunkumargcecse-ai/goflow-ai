# Run goflow.ai in GitHub Codespaces

This setup provisions a browser-based development environment for the existing goflow.ai repository. It is intended for development, demos and testing—not 24/7 production hosting.

## Start

1. Open the repository on GitHub.
2. Select **Code → Codespaces → Create codespace** and choose the `feat/codespaces-cloud-dev-environment` branch (or `main` after this change is merged).
3. Wait for the Codespace to finish creating. The post-create script installs the Python requirements and FFmpeg.
4. The post-start script launches:
   - static Creator Studio at port 3000
   - FastAPI at port 8000
5. In the Codespaces **Ports** panel, open port 3000. Keep both forwarded ports set to **Private**.
6. Copy the forwarded HTTPS URL for port 8000 (the hostname ending in `-8000.app.github.dev`). In Creator Studio, paste it into **Backend API URL**.
7. Copy the one-time API key printed in the Codespaces terminal and enter it in the API key field.

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
