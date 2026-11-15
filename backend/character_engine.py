"""Deterministic character continuity prompt assembly for offline-first Studio workflows."""
from __future__ import annotations


def build_shot_prompt(shot: dict, character: dict | None = None) -> str:
    """Combine shot direction with an optional reusable character bible."""
    sections: list[str] = []
    if character:
        sections.append(
            "CHARACTER IDENTITY — preserve the same individual across every shot: "
            + character.get("identity", "")
        )
        if character.get("appearance"):
            sections.append("FIXED APPEARANCE: " + character["appearance"])
        if character.get("wardrobe"):
            sections.append("WARDROBE: " + character["wardrobe"])
        rules = character.get("continuity_rules") or []
        if rules:
            sections.append("CONTINUITY RULES: " + "; ".join(rules))
        if character.get("negative_guidance"):
            sections.append("AVOID: " + character["negative_guidance"])

    title = (shot.get("title") or "Shot").strip()
    direction = (shot.get("camera_direction") or "").strip()
    notes = (shot.get("visual_notes") or "").strip()
    existing = (shot.get("generation_prompt") or "").strip()
    sections.append(f"SHOT: {title}")
    if direction:
        sections.append("CAMERA DIRECTION: " + direction)
    if notes:
        sections.append("SCENE AND COMPOSITION: " + notes)
    if existing:
        sections.append("SHOT-SPECIFIC GENERATION DIRECTION: " + existing)
    sections.append(
        "CONTINUITY: keep facial features, age, hairstyle, skin tone, body proportions, "
        "and costume details consistent with the supplied character reference. "
        "Do not invent a different person."
    )
    return "\n".join(sections)
