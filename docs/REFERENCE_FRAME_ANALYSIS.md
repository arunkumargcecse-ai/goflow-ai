# Local reference-video frame analysis

After a reference video is imported through `POST /api/v1/studio/reference-videos/inspect`, call:

`POST /api/v1/studio/reference-videos/{media_id}/analyze`

The endpoint uses local FFmpeg scene-score detection and uniform time sampling to extract at most 12 JPEG keyframes. It returns candidate scene-cut count, timestamps, per-frame preview URLs and a basic ordered shot map. Frames are stored under the local Studio output directory in `reference-analysis/{analysis_id}`.

This stage is deliberately limited: FFmpeg scene scores identify visual changes, not semantic scenes. It does not estimate camera movement, detect human poses, identify subjects, transfer motion, or generate video. Those capabilities require separate validated local models and compatible hardware. The endpoint makes no cloud or paid API calls.

Requirements: local `ffmpeg` and `ffprobe` executables on the backend host. Input video remains subject to the existing 100 MB / 180 second ingestion limits.
