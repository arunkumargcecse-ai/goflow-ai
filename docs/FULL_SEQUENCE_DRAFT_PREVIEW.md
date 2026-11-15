# Full-sequence draft preview

Creator Studio provides two sequence-level render actions:

- **Preview full sequence (360p):** renders the entire edited shot map at 360x640 with CRF 25 for quick pacing and audio review.
- **Render final 720p MP4:** renders at 720x1280 with CRF 22 for the final portrait export.

Both actions save the latest shot-map edits first and include the selected narration and background music tracks. Narration starts at 0 seconds; the selected music bed loops at 18% volume. The draft preview is a complete low-resolution MP4, not an individual frame preview.

Use the draft to check shot order, approximate duration, camera pan/zoom, and audio balance before spending time on the full-resolution render. This remains a local FFmpeg still-image workflow, not generative video or true motion transfer.
