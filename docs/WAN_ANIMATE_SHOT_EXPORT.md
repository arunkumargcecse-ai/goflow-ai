# Wan Animate shot workflow export

The shot-map export endpoint creates an editable **ComfyUI canvas workflow JSON** from the repository's pinned Wan 2.2 Animate template. It uploads the selected reference video and character image to the configured local ComfyUI input folder, then binds those filenames and the shot's character-consistent prompt to the template's verified nodes:

- Node 145: `LoadVideo`
- Node 10: `LoadImage`
- Node 21: positive `CLIPTextEncode`

The endpoint returns a JSON file that can be imported into the ComfyUI canvas. It does not submit inference, download models, or claim that a video was generated. The workflow still requires the documented custom nodes, model files, GPU capacity, and a manual ComfyUI run. The 14B workflow is not practical on an Intel Iris Xe laptop.

Endpoint: `POST /api/v1/studio/reference-videos/shot-maps/{map_id}/shots/{shot_index}/export-wan-workflow`

`shot_index` is 1-based. A shot must have an assigned character reference image directly or through its saved character bible.
