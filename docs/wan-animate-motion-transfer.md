# Wan 2.2 Animate motion-transfer readiness

Selected open workflow family: Wan 2.2 Animate. Its Move mode transfers the
driving video's motion to a character supplied as a reference image.

Official guidance:
- https://github.com/Comfy-Org/docs/blob/main/tutorials/video/wan/wan2-2-animate.mdx
- https://comfy.org/hub/workflows/wan2-2-animate-character-animation-and-replacement-c2c4b45bdf5

Authenticated endpoint: GET /api/v1/studio/comfy/wan-animate-readiness

It inspects ComfyUI /object_info and /system_stats for required node classes
and visible device/VRAM information. It does not download weights, install
custom nodes, enqueue a workflow, or call a paid API.

A successful node check does not prove that all model weights are installed or
that the GPU can run the model. Verify weights, licenses, VRAM and a short
local generation before enabling execution. No cloud GPU or paid inference.
