# Studio orchestration API

This milestone connects the existing Phase 2 story planner and Phase 3 provider
contracts to authenticated FastAPI routes.

## Routes

All routes below require `X-Goflow-Key`:

- `POST /api/v1/story/plan`: creates an editable storyboard plan. Without an
  explicitly configured LLM, the offline template planner is used.
- `POST /api/v1/generations`: submits an image or video request through the
  configured provider. The default `mock` provider makes no network request
  and creates no media.
- `GET /api/v1/generations/{generation_id}`: retrieves the durable generation
  request/result record from SQLite.
- `GET /api/v1/studio/providers`: reports zero-cost mode and local capability
  detection. It does not imply a voice model or YouTube account is configured.

## Zero-cost safety

Keep `GOFLOW_GENERATION_PROVIDER=mock` for the free default. Do not add paid
provider credentials or enable billable services without explicit approval.
A mock result is visibly marked `mock` and includes a message that no media
was generated.

## Still required for real production

- Tested, vendor-specific free image/video adapters or local model runners.
- A compatible Tamil TTS voice model installed locally; detecting Piper or
  eSpeak alone does not establish that a Tamil voice is installed.
- Google OAuth client configuration and user authorization for YouTube upload.
- Studio frontend controls, asset download/storage, timeline insertion, render
  composition, and end-to-end acceptance tests using actual generated media.

YouTube Data API uploads require OAuth authorization and are subject to Google
API quota and policy limits. The application must never publish without a
creator-confirmed title, visibility, and scheduled time.
