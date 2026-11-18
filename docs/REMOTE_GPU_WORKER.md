# Secure remote GPU worker for goflow.ai

## Architecture

Keep the goflow.ai API and Creator Studio in GitHub Codespaces. Run ComfyUI,
its custom nodes, and the Wan 2.2 Animate model weights on a separate
NVIDIA-GPU host. The Codespaces backend calls that worker over HTTPS using a
server-side bearer token. The browser never connects directly to ComfyUI.

```text
Creator Studio (port 3000)
        |
        | HTTPS + GOFLOW_API_KEY
        v
goflow.ai API (port 8000, Codespaces)
        |
        | HTTPS + Authorization: Bearer <GOFLOW_COMFYUI_API_KEY>
        v
GPU worker reverse proxy -> ComfyUI (127.0.0.1:8188)
        |
        +-- Wan 2.2 Animate nodes and model weights
        +-- NVIDIA GPU / sufficient VRAM
```

## Backend configuration

Set these environment variables in the Codespaces backend process (do not
place them in HTML, JavaScript, project JSON, or browser local storage):

- `GOFLOW_COMFYUI_URL`: HTTPS base URL of the protected ComfyUI reverse proxy,
  for example `https://gpu-worker.example.net`. Do not include a trailing
  `/prompt` path.
- `GOFLOW_COMFYUI_API_KEY`: high-entropy bearer token accepted by that proxy.

The ComfyUI client sends the bearer token on its server-to-server requests for
workflow submission, queue/history inspection, media upload, output download,
and readiness checks. Redirects are disabled so the authorization header is
not forwarded to another host. If no worker key is configured, the client
retains its local ComfyUI behavior at `http://127.0.0.1:8188`.

Restart the API after setting or rotating environment variables. Then verify:

1. `GET /health` returns healthy.
2. `GET /api/v1/studio/comfy/wan-animate-readiness` reaches the remote worker
   and reports its nodes, model files, and GPU devices.
3. A short, low-resolution test workflow completes before attempting a full
   character/reference-video generation.

## GPU worker requirements

- Linux host with a supported NVIDIA GPU and working NVIDIA driver/CUDA stack.
- ComfyUI bound to loopback only (for example `127.0.0.1:8188`).
- TLS reverse proxy in front of ComfyUI that validates the exact bearer token
  in the `Authorization` header before proxying requests.
- Install the exact Wan 2.2 Animate workflow's required custom nodes and model
  files. The readiness endpoint lists the filenames and nodes it checks.
- Restrict proxy access to the goflow.ai backend where practical. Do not expose
  raw ComfyUI port 8188 to the public internet.

A GPU worker is a separately provisioned service and may incur hourly charges.
Codespaces itself does not provide the NVIDIA GPU needed for Wan 2.2 Animate
14B. This integration does not silently download model weights or start paid
compute.

## Current limitations

This change adds authenticated transport to a remote ComfyUI-compatible
worker. It does not provision a GPU, install model weights, create a cloud
account, or claim that Wan inference is ready. The readiness endpoint and an
actual short generation must pass on the chosen GPU host before enabling
production generation. Keep human review before publishing generated media.
