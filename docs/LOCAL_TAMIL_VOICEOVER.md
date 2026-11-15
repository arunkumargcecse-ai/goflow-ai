# Offline local voiceover generation

Creator Studio exposes `POST /api/v1/studio/voiceovers` to synthesize a narration track on the backend machine. The endpoint returns a Studio `media_id` and media URL; use that ID in the `audio_tracks` list when rendering a composition.

Example request:

```json
{
  "text": "இரவு பன்னிரண்டு மணி. அந்த தொலைபேசி மீண்டும் ஒலித்தது...",
  "engine": "auto",
  "voice": "ta",
  "speed": 145
}
```

## Local engines

- **Piper:** install the Piper executable and a compatible Tamil ONNX voice model. Set `GOFLOW_PIPER_MODEL` to the absolute path of that model. The model is not downloaded automatically.
- **eSpeak NG/eSpeak:** install the executable with the Tamil (`ta`) voice available. The API checks for the voice before synthesis.
- `engine=auto` prefers a configured Piper model, then tries eSpeak. If neither local engine is ready, the API returns a clear service-unavailable error; it does not call a cloud service.

The request accepts 1–5000 characters and a speed of 80–250 words per minute for eSpeak. Output is a WAV asset imported into the Studio media library. Piper's voice characteristics are determined by the configured model; the `speed` field is currently applied to eSpeak only.

This feature provides local speech synthesis, not a promise of a cinematic male Tamil voice. Voice quality and pronunciation depend on the model installed on the worker. A Tamil voice model must be tested on the actual machine before production use.
