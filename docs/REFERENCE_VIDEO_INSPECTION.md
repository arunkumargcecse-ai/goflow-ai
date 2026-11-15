# Reference video inspection

The authenticated endpoint `POST /api/v1/studio/reference-videos/inspect` accepts one MP4, WebM, QuickTime MOV or Matroska upload (maximum 100 MB).

It stores the source as a Studio video asset and returns ffprobe metadata:
- duration, width, height, frame rate, codec and orientation
- a suggested frame-sampling interval and maximum sample count for shot planning
- the Studio media ID and media URL

Example:
```bash
curl -X POST http://localhost:8000/api/v1/studio/reference-videos/inspect \
  -H "X-Goflow-Key: $GOFLOW_API_KEY" \
  -F "file=@reference.mp4"
```

Install FFmpeg (including ffprobe) on the local API host. The endpoint does not send the video to a cloud provider, extract frames, infer human pose, or perform motion transfer. Its `motion_transfer_generated` field is always false. The returned video asset can be used in a later local frame-sampling and motion-analysis stage. Genuine character motion transfer requires a compatible local workflow, model weights and GPU.
