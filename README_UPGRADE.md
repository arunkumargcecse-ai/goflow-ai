# goflow.ai Studio Editor Upgrade

This change records the production workflow and architecture adapted from the supplied STUDIO · AI Video Editor Guide.

## Scope
- Mobile-first creator workspace for project briefs, storyboard shots, style profiles, edit planning and review.
- Separate orchestration API and persistent media worker.
- FFmpeg for media processing, Whisper for word-level transcription, yt-dlp only for permitted references.
- Reference analysis creates an editable `STYLE.md` profile that requires user approval.
- Remotion or HyperFrames can render motion graphics; QC must inspect the actual exported MP4.

## Important limitations
This repository's existing frontend and backend must be inspected and integrated before claiming these capabilities are live. This architecture document does not connect an AI provider or media worker. GitHub Pages hosts static frontend files only; it cannot run FFmpeg, Whisper, yt-dlp or long-running render jobs.

## Safety
Never overwrite source footage, never reuse reference footage/audio/branding/exact designs, keep credentials server-side, use rights-cleared music, and never auto-publish. Human approval is required before export/publishing.

See [docs/STUDIO_VIDEO_EDITOR_PIPELINE.md](docs/STUDIO_VIDEO_EDITOR_PIPELINE.md).
