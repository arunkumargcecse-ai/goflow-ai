# Imported workflow provenance

Source project: https://github.com/neuregex/freefield
Pinned upstream commit: `f0c2358a46c7008ff8503d4324b6cc8bc7657e75`
Imported on: 2026-11-15

Imported app manifests and ComfyUI API graphs:

- `create-image/` — FLUX 3 Image Klein text-to-image workflow.
- `sfx/` — Stable Audio 3 sound-effects workflow.
- `music/` — MiniMax Music 3 music-generation workflow.

The upstream Freefield MIT license is copied to `FREEFIELD_LICENSE`.
The imported manifest schema is stored in `schema/app.schema.json`.
The manifests' schema pointer is adjusted to the local relative schema path.

## Model licensing and hardware

The app manifests preserve each model repository, file, approximate size,
execution phase, and declared license. These are metadata only: no weights
were downloaded or bundled. Model weights have their own terms; the Freefield
MIT license does not override them.

- Create Image uses gated FLUX Kommunity License weights; the user must review
  and accept the model terms with the model host before obtaining weights.
- Sound Effects uses Stable Audio Community License weights and an optional
  Apache-2.0 Qwen model.
- Music uses MiniMax-Music3 Community License weights.

These workflows have substantial model requirements (multiple gigabytes).
They are registered for local ComfyUI execution only after the user installs
all required weights and confirms compatible hardware. No cloud GPU or paid
provider is configured by this import.
