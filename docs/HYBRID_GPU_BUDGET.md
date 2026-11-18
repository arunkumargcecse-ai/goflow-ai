# goflow.ai hybrid GPU deployment and budget controls

## Target architecture

Keep Creator Studio, FastAPI, SQLite, project assets and final FFmpeg assembly on the Windows laptop. Run ComfyUI and Wan 2.2 Animate on a rented NVIDIA GPU worker only for generation. The laptop talks to the worker through the server-side ComfyUI client; browser JavaScript must never receive the worker URL or bearer token.

```text
Windows 11 laptop
  Creator Studio + FastAPI + SQLite + FFmpeg
          | authenticated HTTPS (backend only)
          v
On-demand Linux NVIDIA GPU worker
  HTTPS reverse proxy -> ComfyUI on 127.0.0.1:8188
  Wan 2.2 Animate nodes + model weights
```

## Required backend environment

Configure these in the FastAPI process environment, not in HTML, browser storage, screenshots, or committed files:

- GOFLOW_COMFYUI_URL: HTTPS URL of the protected ComfyUI reverse proxy.
- GOFLOW_COMFYUI_API_KEY: high-entropy bearer token accepted by the proxy.
- GOFLOW_GPU_MONTHLY_BUDGET_INR=1000: monthly estimated-compute ceiling.
- GOFLOW_GPU_HOURLY_RATE_INR: the selected worker's actual advertised hourly rate converted to INR.
- GOFLOW_GPU_JOB_MAX_MINUTES=20: conservative maximum runtime reserved for each accepted generation request.

For a remote worker, submissions fail closed if the hourly rate is missing or zero. Before each ComfyUI workflow submission, goflow.ai reserves hourly-rate × max-runtime/60 from a UTC-calendar-month SQLite ledger. A submission that ComfyUI rejects releases its reservation. The authenticated GET /api/v1/studio/comfy/gpu-budget endpoint reports the cap, estimates, remaining allowance and configured rate.

The ledger is a conservative estimate, not provider billing telemetry. Actual charges can differ due to minimum billing increments, storage, idle time, bandwidth, taxes, exchange rates, and provider-specific fees. Check the provider invoice. Update the configured hourly rate whenever the rental price changes. Reservations are not automatically reconciled against invoices or refunded when a completed job uses less than the configured maximum runtime.

## Cost-control operating procedure

1. Create a GPU worker only when a Wan job is ready to run.
2. Choose an hourly rental with a clearly displayed rate and adequate VRAM. The project's current readiness guidance uses 24 GiB as a conservative planning baseline, not a guarantee.
3. Set the hourly rate and job maximum before submitting. For example, at ₹75/hour and 20 minutes, each accepted job reserves ₹25.
4. Check GET /api/v1/studio/comfy/gpu-budget before a generation session.
5. Start ComfyUI, run a short low-resolution validation, then submit the intended workflow.
6. Stop or destroy the GPU instance immediately after generation and download outputs to local storage. Do not leave an hourly instance idle.
7. Check provider usage and invoices independently.

The current integration does not create, start, stop, or destroy cloud instances. It cannot enforce a hard provider-side spend ceiling or stop an instance automatically. Those actions require provider API credentials and a provider-specific lifecycle adapter, which are deliberately not guessed or stored in this repository. Keep the provider dashboard's own spend alerts and manual shutdown controls enabled.

## Wan 2.2 Animate readiness

A successful HTTPS connection is not proof that Wan is ready. The protected GET /api/v1/studio/comfy/wan-animate-readiness check must show the required custom nodes, exact model files and a visible CUDA device. Then complete a short test generation. The model/node check does not download weights or benchmark inference.

Never expose raw ComfyUI port 8188 to the public internet. Bind ComfyUI to loopback on the worker and put an authenticated TLS reverse proxy in front of it. Keep the bearer key server-side and rotate it if it appears in a screenshot or log.