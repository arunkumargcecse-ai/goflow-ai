# Wan 2.2 Animate workflow asset

goflow.ai vendors the official Comfy-Org ComfyUI UI workflow template at:

- Upstream: https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_wan2_2_14B_animate.json
- Source file: `backend/workflows/wan2-2-animate/video_wan2_2_14B_animate.json`

The imported file is the official **ComfyUI UI workflow**, not an API-format
prompt graph. It is preserved for inspection/import into ComfyUI and must not
be sent directly to `/prompt`. The graph currently includes 40 nodes and uses
`LoadImage` node 10 and `LoadVideo` node 145 as the reference inputs.

## Required custom nodes

The upstream graph references:
- `comfyui_controlnet_aux` (DWPose / PixelPerfectResolution)
- `ComfyUI-KJNodes` (PointsEditor and related utilities)
- Core ComfyUI nodes including Wan Animate sampling, video loading and output.

## Model files

The upstream graph's notes identify these model families/files:
- Wan 2.2 Animate 14B diffusion model (BF16 or Kijai FP8 scaled build)
- UMT5-XXL text encoder
- CLIP Vision H
- Wan 2.1 VAE
- Optional LightX2V I2V LoRA and Animate relight LoRA

Exact file variants, directories, upstream links and licenses must be verified
against the installed ComfyUI version and the upstream workflow notes before
download. The model files are large. No model weights are bundled or downloaded
by this PR.

## Input and output

- Character reference: LoadImage node 10.
- Driving video: LoadVideo node 145.
- Move mode: follow the official ComfyUI guide to disconnect
  `background_video` and `character_mask` from the Video Sampling and output
  subgraph. Mix mode replaces the performer in the input video.
- WanAnimateToVideo requires width and height to be multiples of 16.
- Start with a short, low-resolution clip to validate VRAM and node compatibility.

## Current goflow.ai status

This PR imports the source template only. It does not yet convert the UI graph
into an API prompt, bind uploaded `image_ref` / `video_ref` values to its
nodes, install custom nodes, verify model weights, or execute inference.
The workflow remains unavailable for generation until those steps are tested.

No paid API, cloud GPU, or automatic download is used.
