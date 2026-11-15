"""Conservative hardware guidance for local Wan 2.2 Animate execution.

This is an advisory gate, not a benchmark or a promise that a model will fit.
"""
from __future__ import annotations

_GIB = 1024 ** 3
_RECOMMENDED_VRAM_BYTES = 24 * _GIB


def assess_wan_hardware(devices: list[dict]) -> dict:
    """Summarize ComfyUI-reported accelerators without probing or changing hardware."""
    normalized = [item for item in devices if isinstance(item, dict)]
    accelerators = []
    for item in normalized:
        kind = str(item.get("type", "")).lower()
        name = str(item.get("name", "unknown"))[:160]
        total = item.get("vram_total_bytes")
        is_cuda = "cuda" in kind or "nvidia" in kind or "cuda" in name.lower()
        accelerators.append({
            "name": name,
            "type": kind or "unknown",
            "cuda_capable": is_cuda,
            "vram_total_bytes": total if isinstance(total, int) and total >= 0 else None,
        })
    cuda_devices = [item for item in accelerators if item["cuda_capable"]]
    max_vram = max((item["vram_total_bytes"] or 0 for item in cuda_devices), default=0)
    if not cuda_devices:
        status = "no_cuda_accelerator"
        message = ("No CUDA/NVIDIA accelerator was reported by ComfyUI. Wan 2.2 Animate "
                   "14B is not a practical CPU-only workload; use a compatible GPU worker.")
    elif max_vram < _RECOMMENDED_VRAM_BYTES:
        status = "below_recommended_vram"
        message = ("The reported CUDA VRAM is below the conservative 24 GiB planning "
                   "baseline. A quantized/offload setup may differ, but generation is not "
                   "validated and may fail or be extremely slow.")
    else:
        status = "gpu_visible_review_required"
        message = ("A CUDA device meets the 24 GiB planning baseline. This is not a "
                   "generation guarantee; confirm model files, custom nodes, precision, "
                   "offload configuration and a short test render.")
    return {
        "status": status,
        "recommended_vram_bytes": _RECOMMENDED_VRAM_BYTES,
        "max_reported_cuda_vram_bytes": max_vram or None,
        "accelerators": accelerators,
        "execution_supported": False,
        "message": message,
        "note": "Advisory only; ComfyUI system_stats is the source of device visibility. No model was loaded or benchmarked.",
    }
