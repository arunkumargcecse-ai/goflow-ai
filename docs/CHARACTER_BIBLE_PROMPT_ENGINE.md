# Character Bible and Shot Prompt Engine

Project VEL now supports reusable, local character bibles for consistent prompt construction.

## API

- `GET /api/v1/studio/characters` — list saved character profiles.
- `POST /api/v1/studio/characters` — create a profile with identity, appearance, wardrobe, continuity rules, negative guidance, and up to eight Studio image references.
- `GET /api/v1/studio/characters/{character_id}` — retrieve a profile.
- `POST /api/v1/studio/reference-videos/shot-maps/{map_id}/build-prompts` — assemble deterministic shot prompts.

Character reference IDs must point to imported Studio image media. Character profiles are stored in the existing local SQLite database. No external API, paid service, or model inference is used.

## Current boundary

The shot-map prompt builder is a deterministic prompt assembly step. It does not perform face recognition, identity verification, image generation, video generation, pose estimation, or motion transfer. To apply a character bible to a shot, the shot map may include a `character_id` field referencing a saved character profile. Existing `character_media_id` image assignments remain supported as image references, but do not automatically imply a semantic character profile.
