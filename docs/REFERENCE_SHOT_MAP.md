# Reference shot map

Once a reference video is imported and analysed, Creator Studio can extract up to 12 representative frames, preview them, and edit a shot card for each frame.

Each shot stores:
- source frame and timestamp
- editable shot title and intended output duration
- camera direction
- visual continuity notes
- generation prompt
- optional imported Studio image ID for character reference (API-supported)

Save the plan with `POST /api/v1/studio/reference-videos/{media_id}/shot-map`. Retrieve it with `GET /api/v1/studio/reference-videos/shot-maps/{map_id}`.

The shot map is a production brief, not generated video. It does not yet estimate camera motion, infer poses, identify people, or invoke Wan. Character-image assignment is supported by the API only when the image already exists in the Studio media library; the current editor focuses on frame-by-frame shot planning and prompt authoring.
