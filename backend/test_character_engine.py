import unittest

from character_engine import build_shot_prompt


class CharacterPromptTests(unittest.TestCase):
    def test_includes_character_bible_and_shot_direction(self):
        prompt = build_shot_prompt(
            {
                "title": "Rainy arrival",
                "camera_direction": "Slow push-in, eye level",
                "visual_notes": "Rainy railway platform at night",
                "generation_prompt": "The lead turns toward the camera",
            },
            {
                "identity": "A 30-year-old Tamil man",
                "appearance": "Short black hair, trimmed beard",
                "wardrobe": "Dark charcoal jacket",
                "continuity_rules": ["Keep the same hairstyle", "No glasses"],
                "negative_guidance": "No face shape changes",
            },
        )
        for expected in (
            "A 30-year-old Tamil man", "Short black hair", "Dark charcoal jacket",
            "Keep the same hairstyle", "Rainy railway platform", "Slow push-in",
            "No face shape changes",
        ):
            self.assertIn(expected, prompt)

    def test_works_without_character_profile(self):
        prompt = build_shot_prompt({"title": "Establishing shot"})
        self.assertIn("SHOT: Establishing shot", prompt)
        self.assertIn("CONTINUITY:", prompt)


if __name__ == "__main__":
    unittest.main()
