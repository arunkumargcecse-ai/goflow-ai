# goflow.ai Studio Editor Pipeline

This adapts the supplied STUDIO · AI Video Editor Guide into goflow.ai.

## Three-stage workflow

1. **Tool readiness:** verify FFmpeg, Whisper with word timestamps, yt-dlp, and a chosen renderer. Installed is not the same as tested.
2. **Style intelligence:** inspect 3–5 permitted references, extract representative frames, inspect transcripts, create an editable `STYLE.md`, and wait for user approval.
3. **Draft production:** select the intended source video, transcribe, propose meaning-preserving cuts, preserve natural pauses, create captions and original motion graphics, mix rights-cleared music, render a new version, inspect it, and wait for approval.

## Components

- FastAPI orchestration API: projects, jobs, status, approvals and version metadata.
- FFmpeg worker: media probe, cuts, joins, audio mix, encoding and thumbnails.
- Whisper adapter: local transcription and word timestamps; human transcript review remains required.
- yt-dlp adapter: download only references the user is permitted to use.
- Reference analyser: sampled frames, transcript and shot/pacing observations.
- `STYLE.md`: approved reusable visual/audio rules.
- Remotion renderer: React titles, captions, diagrams and motion graphics.
- HyperFrames renderer: alternative HTML-to-video route.
- QC worker: actual output stream, duration, resolution, audio, caption and playback checks.

Use Remotion **or** HyperFrames for an individual render, choosing the simpler fit.

## Rights, safety and data

- Never overwrite raw footage, projects or prior exports.
- Download only permitted reference material.
- Never reuse reference footage, audio, branding or exact designs in exports.
- Use user-supplied music with rights or music with a verified licence. If unclear, render voice-only.
- Never auto-publish. Human review is mandatory.
- Keep API keys server-side, never in browser code or Git.
- Report checks as passed only when actually executed; unavailable checks remain visibly unavailable.

## Deployment reality

GitHub Pages serves the static frontend only. It cannot execute FFmpeg, Whisper, yt-dlp or video rendering. These require a separate worker runtime with adequate CPU, disk and persistent job storage. Do not run long media jobs inside a short-lived web request without validating host limits.

## Acceptance checks

- Tool readiness reports installed, version and real test result separately.
- Reference analysis cannot claim inspection if frames/transcript were not obtained.
- Transcripts retain word timestamps and uncertainty for review.
- Cut proposals preserve meaning and natural pauses.
- Captions are retimed to the edited timeline and checked for safe margins.
- Renders create new versioned outputs and preserve source media.
- QC inspects the actual exported MP4.
- Export remains a draft until human approval.
