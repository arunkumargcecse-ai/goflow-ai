# Wan 2.2 Animate hardware-aware readiness

The local readiness response now includes a conservative hardware advisory derived
from ComfyUI's `/system_stats` device list.

- No reported CUDA/NVIDIA accelerator: the 14B Animate workflow is not a practical
  CPU-only workload.
- Less than 24 GiB reported CUDA VRAM: flagged below a conservative planning baseline.
- 24 GiB or more: still requires checking model files, custom nodes, precision,
  offload configuration and a short real render.

The 24 GiB value is a planning heuristic, not an official minimum or a guarantee.
Quantization and offload can change memory requirements and performance. The check
does not inspect private hardware outside ComfyUI, load weights, benchmark, download
anything, enqueue jobs or enable execution.

For a laptop with Intel Iris Xe integrated graphics and no NVIDIA CUDA GPU, expect
`no_cuda_accelerator`. Keep local FFmpeg editing and prompt/shot planning on that
machine; export the workflow for a capable local GPU workstation when available.
