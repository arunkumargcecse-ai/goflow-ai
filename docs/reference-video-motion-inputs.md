# Reference-video motion input milestone

This change adds a secure, local-only upload path for reference videos and typed
video-file bindings in trusted ComfyUI workflow manifests.

## API

- POST /api/v1/studio/comfy/upload-video accepts MP4, WebM, and QuickTime
  uploads up to 100 MB and returns a validated video_ref for a local ComfyUI
  workflow.
- The endpoint requires the normal goflow API key authentication.
- The upload is sent only to the configured GOFLOW_COMFYUI_URL; no cloud
  generation provider or paid API is contacted.
- Workflow manifests may declare an input with "type": "video". Its value
  must be a safe local ComfyUI input reference, just like an image input.

## Important limitation

This is the reference-media ingestion and workflow-binding foundation, not a
complete motion-transfer model integration. A runnable motion-transfer workflow
still needs a compatible ComfyUI API graph, its custom nodes, model weights,
and a hardware compatibility check. goflow.ai must not label a motion-transfer
workflow as ready until those assets are installed and tested locally.

Use only videos and photos you own or are authorized to process. Large uploads
are bounded at 100 MB; model downloads and GPU workloads are deliberately not
started by this change.
