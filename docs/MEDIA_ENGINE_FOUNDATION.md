# goflow.ai Media Engine Foundation

## Implemented Studio workflow

The Creator Studio now has a source-video upload, API-key entry, trim start/duration, render preset, job polling and authenticated MP4 download. The selected project aspect ratio determines the output canvas. The browser does not save the API key in project JSON or local autosave.

## API flow

1. `POST /api/v1/media/upload` — multipart form field named `file`; requires `X-Goflow-Key`.
2. `POST /api/v1/jobs/render` — JSON body with `media_id`, optional `start_seconds`, `duration_seconds`, output dimensions and preset; requires `X-Goflow-Key`.
3. `GET /api/v1/jobs/{job_id}` — status and progress.
4. `GET /api/v1/jobs/{job_id}/output` — completed MP4; requires `X-Goflow-Key`.

## Deploy backend container

`backend/Dockerfile` installs FFmpeg/FFprobe and starts FastAPI. Deploy it as a Docker web service with the Dockerfile located in `backend/` (or set the build context to `backend`). Set these environment variables in the hosting dashboard:

- `GOFLOW_API_KEY`: generate a long random secret; never commit it or put it in a public repository.
- `GOFLOW_CORS_ORIGINS`: `https://arunkumargcecse-ai.github.io` (the browser Studio origin).
- `GOFLOW_DATA_DIR`: `/var/data`.
- `GOFLOW_MAX_UPLOAD_BYTES`: optional; defaults to 524288000.

Attach a persistent disk mounted at `/var/data`. Without persistent storage, uploaded files, outputs and the SQLite database can disappear during restart or redeploy. Persistent disks and always-on compute may require a paid hosting plan; do not enable paid resources without checking the current price and approving the charge. GitHub Pages does not host this backend.

In the Studio's Quality & tools tab, set Backend URL to the deployed HTTPS service URL, enter the `GOFLOW_API_KEY` into the Media API key field, check API health, then upload and render a short test clip.

## Security and operational limits

- Upload, render creation and output downloads require the server-side API key. If `GOFLOW_API_KEY` is absent, media operations fail closed with HTTP 503.
- The job status endpoint uses unguessable UUIDs but is currently readable without a key; do not put sensitive source names in filenames.
- This is a single-user starter API key, not full account authentication. Add rate limits, quotas, abuse monitoring and per-user access controls before broader public use.
- The render endpoint currently uses FastAPI BackgroundTasks. Job records persist in SQLite, but execution is not yet a separately supervised durable worker; process restarts may leave queued/processing records needing recovery.
- Keep source uploads separate from exports. This pipeline trims/re-encodes video; it is not generative video.

## Current boundaries

Whisper transcription, word-level captions, AI image/video/Tamil voice providers, reference-video analysis, distributed workers and full MP4 quality-control playback checks are not connected. Capabilities remain explicitly disconnected until integrated and tested.
