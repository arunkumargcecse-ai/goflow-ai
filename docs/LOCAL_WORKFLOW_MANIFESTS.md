# Local ComfyUI workflow manifests

goflow.ai includes three pinned Freefield app manifests and API graphs (Create Image, Sound Effects, and Music). It can also expose additional locally installed, Freefield-compatible app manifests as Creator Studio forms and submit their bound API graphs to the configured local ComfyUI instance.

## Install a workflow

Create one folder per workflow under `backend/workflows/` (or the directory
configured by `GOFLOW_WORKFLOW_DIR`):

```text
backend/workflows/
  sample-image/
    app.json
    workflow.api.json
```

The manifest follows Freefield's `app.json` shape. The minimum fields are
`id`, `name`, `section`, `status`, `inputs`, `outputs`, and `models`.
Set `status` to `ready` only after the graph and every declared binding have
been checked. The workflow filename must be a local `.api.json` file.

Example input:

```json
{
  "id": "prompt",
  "type": "text",
  "label": "Prompt",
  "required": true,
  "bind": [{"node": "6", "field": "text"}]
}
```

The referenced node and input field must exist in the API graph. Numeric
inputs can declare `min` and `max`; select inputs can declare allowed
`options`. The current runner supports text, textarea, number, slider,
select (including numeric option values and option-driven graph settings), toggle, seed, and image controls. Image inputs accept only safe `image_ref` values returned by the local upload endpoint. Video/audio inputs, multi-select modes, and presets are not yet supported by this runner.

## API

The catalogue endpoint includes a `local_workflows` list containing only installed apps whose manifests and graph bindings validate. All routes use the normal goflow API-key authentication:

- `GET /api/v1/studio/workflows/{workflow_id}` returns the validated form,
  declared outputs, model license metadata, custom-node requirements, and VRAM
  metadata.
- Completed jobs expose `imported_media` entries. Supported image, video, GIF, and audio outputs are downloaded from the local ComfyUI `/view` endpoint, copied into the goflow data directory, and recorded in the Studio media library. Repeated status polls reuse the existing imported record. `GET /api/v1/studio/media/{media_id}` serves the stored file through the authenticated API.
- `POST /api/v1/studio/comfy/upload-image` accepts a multipart `file` field containing a PNG, JPEG, or WebP image (maximum 20 MB), uploads it to the configured local ComfyUI input directory, and returns an `image_ref` suitable for a manifest image input bound to a ComfyUI `LoadImage` node. The endpoint never accepts a ComfyUI URL from the browser.
- `POST /api/v1/studio/workflows/{workflow_id}/run` accepts
  `{"values":{"prompt":"A cinematic rainy street"}}`, applies only declared
  manifest bindings to a copy of the trusted local graph, and submits it to
  ComfyUI.

The browser cannot supply an arbitrary graph through this endpoint. Uploaded references stay on the configured local ComfyUI instance; goflow.ai does not forward them to a paid provider. Unknown
input keys, unsupported controls, invalid values, unresolved bindings, draft
manifests, and path traversal are rejected. The existing low-level ComfyUI
submit endpoint remains available for trusted administrator workflows.

## Safety and cost

This runner does not download workflows, custom nodes, or model weights. It
does not provision cloud GPUs or call paid providers. ComfyUI execution uses
the local worker configured by `GOFLOW_COMFYUI_URL`; local electricity and
network costs may apply.

A ComfyUI graph and its custom nodes are executable code. Install only
workflows and custom nodes you trust, pin and review their source, and verify
each model's license before downloading or using its weights. A Freefield
repository license does not automatically license third-party model weights.


## Bundled Freefield workflows

The repository pins Freefield at commit
`f0c2358a46c7008ff8503d4324b6cc8bc7657e75` and includes:

- `create-image` — gated FLUX 3 Image Klein image generation.
- `sfx` — Stable Audio 3 sound effects.
- `music` — MiniMax Music 3 music generation.

See [workflow provenance and model licensing](../backend/workflows/UPSTREAM.md).
Only manifests and workflow JSON are included. Model weights are not included
or downloaded. Create Image requires acceptance of the FLUX Kommunity License;
the audio models have their own community licenses. These are large workflows
and are not confirmed to fit the user's laptop until GPU/VRAM is checked.
