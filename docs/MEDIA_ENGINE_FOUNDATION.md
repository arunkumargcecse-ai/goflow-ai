# goflow.ai Media Engine Foundation

## Implemented API slice

- Upload source video files (MP4, MOV, MKV, WebM, M4V) with a configurable size limit.
- Probe duration and video dimensions when FFprobe is installed.
- Store source files separately from exports; source uploads are never overwritten.
- Create SQLite-backed media and render-job records.
- Render a new MP4 using FFmpeg with a trim range, aspect-preserving scale/pad, H.264 video, AAC audio and fast-start metadata.
- Poll job status and retrieve a completed MP4.
- Report FFmpeg/FFprobe availability from the actual host PATH.

## API flow

1. `POST /api/v1/media/upload` — multipart form field named `file`.
2. `POST /api/v1/jobs/render` — JSON body with `media_id`, optional `start_seconds`, `duration_seconds`, output dimensions and preset.
3. `GET /api/v1/jobs/{job_id}` — status and progress.
4. `GET /api/v1/jobs/{job_id}/output` — completed MP4.

The render endpoint currently uses FastAPI BackgroundTasks. Job metadata is stored in SQLite, but execution is not yet a separately supervised durable worker: a process restart can leave a queued/processing record that needs recovery. The next infrastructure milestone is a dedicated worker process and durable queue.

## Runtime configuration

- `GOFLOW_DATA_DIR`: persistent writable directory for SQLite, uploads and outputs. Defaults to `backend/data`.
- `GOFLOW_MAX_UPLOAD_BYTES`: maximum upload size; defaults to 500 MiB.
- `GOFLOW_CORS_ORIGINS`: comma-separated allowed browser origins. Set this to the deployed Studio origin in production; the default wildcard is for initial integration only.
- Install FFmpeg and FFprobe on the backend/worker host. GitHub Pages cannot execute either tool.
- Mount `GOFLOW_DATA_DIR` on persistent storage. Ephemeral host disks will lose source files, exports and the job database on restart/redeploy.

## Current boundaries

This slice is a real local-file trim/re-encode pipeline, not generative video. It does not yet include Whisper transcription, word-level captions, AI image/video/Tamil voice providers, reference-video analysis, distributed workers, or full MP4 quality-control playback checks. Provider and transcription capabilities remain explicitly disconnected until integrated and tested.

Do not expose the upload API publicly without authentication, rate limits, storage quotas and a production CORS allowlist. Do not store provider secrets in the browser or repository.
