# Phase 2 — AI story and storyboard engine

The story planner accepts a creator brief and returns a structured, editable
pre-production plan: logline, synopsis, characters, locations, scene beats,
camera directions, dialogue/voiceover slots, sound design, image prompts,
video prompts, and continuity notes.

## Modes
- Offline template mode is the default and makes no network calls. It is a
  draft scaffold, not a claim of AI-generated writing.
- An OpenAI-compatible chat completion endpoint can be enabled on the backend
  with `GOFLOW_LLM_BASE_URL`, `GOFLOW_LLM_MODEL`, and
  `GOFLOW_LLM_API_KEY`. Keep these values in the backend environment only.

The Studio must require creator review before generated plans become approved
production assets. Provider calls are optional and may incur charges according
to the provider's own pricing; do not enable one without explicit approval.
