# Studio multi-track audio composition

The Studio render API now supports up to 20 independently timed audio tracks in
addition to the existing optional `audio_media_id` soundtrack field.

Example request body:

```json
{
  "clips": [
    {"media_id": "32-character-media-id", "duration": 8, "motion": "zoom_in"}
  ],
  "audio_tracks": [
    {"media_id": "voice-media-id", "start_seconds": 0, "volume": 1.0, "loop": false},
    {"media_id": "music-media-id", "start_seconds": 0, "volume": 0.18, "loop": true},
    {"media_id": "impact-media-id", "start_seconds": 3.2, "volume": 0.8, "loop": false}
  ],
  "width": 720,
  "height": 1280,
  "preset": "veryfast",
  "crf": 22
}
```

- `start_seconds` positions the track on the final timeline.
- `volume` accepts 0.0 through 2.0; use lower values for music under dialogue.
- `loop` repeats a short music/ambience asset to cover the composition.
- Multiple tracks are mixed locally by FFmpeg and limited to reduce clipping.
- The legacy `audio_media_id` field remains supported for existing clients.
- Audio tracks must reference audio assets already imported into Studio.

This is audio timeline mixing, not text-to-speech generation. Tamil narration
still requires a separately installed local TTS engine/model or an imported
voice recording. No paid API or cloud inference is invoked.
