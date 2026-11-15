# Local ComfyUI workflow manifests

goflow.ai can expose a locally installed, Freefield-compatible app manifest as a
Creator Studio form and submit its bound API graph to the configured local
ComfyUI instance.

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
select, toggle, and seed controls. File uploads, image/video/audio inputs,
multi-select modes, and presets are not yet supported by this runner.

## API

All routes use the normal goflow API-key authentication:

- `GET /api/v1/studio/workflows/{workflow_id}` returns the validated form,
  declared outputs, model license metadata, custom-node requirements, and VRAM
  metadata.
- `POST /api/v1/studio/workflows/{workflow_id}/run` accepts
  `{"values":{"prompt":"A cinematic rainy street"}}`, applies only declared
  manifest bindings to a copy of the trusted local graph, and submits it to
  ComfyUI.

The browser cannot supply an arbitrary graph through this endpoint. Unknown
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
