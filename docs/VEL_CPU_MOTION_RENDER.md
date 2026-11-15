# VEL CPU-friendly scene motion and render path

This milestone adds a real, local FFmpeg motion path for storyboard stills. It
does not pretend that a still-image camera move is AI-generated video.

## Supported still-image motion

The authenticated Studio render API accepts a per-clip `motion` value:

- `zoom_in` (default): slow, bounded push-in.
- `zoom_out`: slow pull-back.
- `pan_left` and `pan_right`: subtle horizontal camera drift.
- `static`: no camera animation.

Example request clip:

```json
{
  "media_id": "32-character-media-id",
  "duration": 5,
  "motion": "zoom_in"
}
```

The renderer creates 30 fps H.264 MP4 output, supports 9:16 portrait
dimensions, and can mix an uploaded audio asset underneath the sequence.
Use 720x1280 for a lower-load 720p portrait render; 1080x1920 remains the
default. On a laptop CPU, choose the `veryfast` preset and CRF 21-23 for
preview renders.

## What this does and does not do

This is a practical no-cost fallback for machines without a supported AI GPU:
it animates supplied still images with FFmpeg and composes real source-video
clips. It does not synthesize new character motion, infer unseen poses, or
transfer motion from a reference video. Those capabilities still require a
compatible video diffusion model/runtime and substantial GPU memory. The
Wan 2.2 Animate 14B template is retained as an optional high-end ComfyUI path,
not a promise that an Intel Iris Xe laptop can execute it.

## Audio and Tamil narration

A soundtrack can be supplied using `audio_media_id` on the Studio render
request. Local speech-engine discovery is exposed by the providers endpoint;
a Tamil voice model must be installed and validated before claiming Tamil
TTS is available. Do not silently substitute an unrelated language voice.
The render API currently mixes one uploaded soundtrack, not multi-track
dialogue, music and effects automation.

## Validation

Run from `backend/`:

```powershell
python -m unittest test_studio_composer.py
python -m unittest discover -v
python -m compileall -q .
```

A passing unit test verifies filter construction and API-side behavior; a
real end-to-end render on the target laptop is still required to verify local
FFmpeg installation, speed, and output quality.
