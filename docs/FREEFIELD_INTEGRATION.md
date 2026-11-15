# Freefield / ComfyUI integration

goflow.ai is adopting useful architecture from [neuregex/freefield](https://github.com/neuregex/freefield), not copying its entire 120-app product or replacing Creator Studio.

## Patterns being reused

Freefield's public repository is MIT-licensed (Copyright 2026 Sammir Femat). Its useful engineering patterns are:
- Manifest-driven apps: inputs, node bindings, outputs, models, model phases and license metadata.
- ComfyUI API-format workflows as reusable execution graphs.
- A generic runner that validates/coerces form values before binding workflow nodes.
- Queue/history/progress in the browser.
- Model-aware GPU memory management when switching workflows.
- Explicit model catalogues with source, size, license and VRAM requirements.

Retain upstream MIT copyright and license notices when copying or modifying upstream source. Model weights and custom nodes have their own licenses; the repository MIT license does not relicense those assets.

## goflow.ai integration boundary

FastAPI remains the orchestration and FFmpeg layer. ComfyUI is an optional, separately installed local worker:

```
Creator Studio -> authenticated goflow API -> FastAPI + SQLite + FFmpeg
                                      |
                                      v
                         GOFLOW_COMFYUI_URL (server only)
                                      |
                                      v
                          ComfyUI API :8188 (GPU worker)
                                      |
                                      v
                     model loaders + custom nodes + outputs
```

Implemented in this milestone:
- Fixed-origin ComfyUI HTTP client. Browser requests cannot choose the ComfyUI host.
- Authenticated queue/status endpoint.
- Authenticated workflow submission endpoint for ComfyUI API-format graphs.
- Authenticated job-history lookup by ComfyUI prompt ID.
- Workflow-shape and prompt-ID validation.
- Mock generation remains the default; ComfyUI is opt-in and does not download models or provision cloud GPUs.

Configure the backend with `GOFLOW_COMFYUI_URL=http://127.0.0.1:8188` (or the address of a worker you own). Keep the worker private; do not expose port 8188 directly to the public internet. The existing goflow API key protects Studio endpoints, but ComfyUI itself also needs network controls.

## Not yet imported / production-ready

- The upstream catalogue contains 120 apps and many large workflow JSON files. We will import selected apps incrementally, not bulk-copy all 120.
- A full manifest registry, UI-generated forms, model download manager, ComfyUI custom-node installer, GPU VRAM estimator and model-unload gateway are subsequent milestones.
- This API currently accepts an API-format workflow graph; it does not yet translate a Freefield `app.json` manifest into a runnable graph or upload reference media.
- ComfyUI output files are not yet copied into goflow's media library/timeline.
- Real execution requires exact ComfyUI version, custom nodes, model files, hardware and each model's own license. Some upstream recipes use gated weights or need GPUs with far more VRAM than a typical laptop.
- Hosted Modal support is deliberately excluded from our ₹0 budget plan.

## Suggested staged import

1. Import the Freefield manifest schema and registry, preserving model and license metadata.
2. Import a small verified starter set: image generation, image-to-video, cinematic camera controls, sound effects and music.
3. Add safe file upload, output retrieval, progress events and media-library persistence.
4. Connect generated assets to storyboard shots and FFmpeg timeline rendering.
5. Add Tamil TTS as a separate local voice provider.

## Upstream
- Repository: https://github.com/neuregex/freefield
- License: MIT; see `LICENSE` in the upstream repository.
- Model and custom-node licenses listed by each upstream app remain separately applicable.
