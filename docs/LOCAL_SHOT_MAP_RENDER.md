# Local shot-map MP4 rendering

Creator Studio can turn a saved reference shot map into a local 720p portrait MP4.

1. Upload a reference video and extract representative frames.
2. Review shot durations and camera direction; assign a character bible where desired.
3. Click **Render 720p MP4 locally**.
4. The backend saves the latest shot map, selects each shot's assigned character reference image when available, and otherwise uses that shot's extracted reference frame.
5. FFmpeg renders the ordered stills with bounded camera-motion presets and returns an MP4 download.

The default output is 720x1280, 30 fps, veryfast, CRF 22. This is intentionally configured for modest local hardware. Existing narration and music tracks can be attached through the render API's audio_tracks field.

## Important limitations

This feature is a local **cinematic still-to-video renderer**, not generative video, pose transfer, or true motion transfer. The camera direction is approximated using FFmpeg zoom/pan over still images. It does not recreate body movement, lip sync, moving backgrounds, or the exact motion of the source video. Use a machine with FFmpeg installed and sufficient free disk space. No cloud inference, paid API, or model download is involved.

API: POST /api/v1/studio/reference-videos/shot-maps/{map_id}/render

Optional JSON body:
```json
{
  "width": 720,
  "height": 1280,
  "preset": "veryfast",
  "crf": 22,
  "audio_tracks": []
}
```

The response contains a render_id and status_url. Poll GET /api/v1/studio/renders/{render_id}; when status is completed, download the MP4 from its output_url.