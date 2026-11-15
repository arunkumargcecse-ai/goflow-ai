# Per-shot preview workflow

Creator Studio now offers a short preview for each editable reference shot before the full sequence is rendered.

1. Extract frames from a reference video and edit each shot's duration, camera direction, notes, and character assignment.
2. Click **Preview shot** on an individual shot card.
3. The UI saves the latest shot-map edits, then queues a short local FFmpeg preview.
4. A 360x640 MP4 preview appears inline on that shot card. Review framing and the approximate pan/zoom direction.
5. Adjust the shot and preview again, then render the complete 720x1280 sequence.

Previews use a 2.5-second default duration, 360x640 output, the fast FFmpeg preset, and CRF 25. The preview uses the assigned character reference image when available; otherwise it uses the extracted reference frame.

## Capability boundary

These previews are cinematic still-image previews. They show the chosen still, framing, and approximate camera movement; they do not generate body motion, transfer source-video motion, or create lip sync. No cloud inference, paid API, or model download is used.

API: POST /api/v1/studio/reference-videos/shot-maps/{map_id}/shots/{shot_index}/preview

Poll the returned render_id using GET /api/v1/studio/renders/{render_id}. The completed MP4 is served by the returned output_url.