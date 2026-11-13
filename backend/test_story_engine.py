import unittest
from story_engine import StoryPlanRequest, create_story_plan


class StoryEngineTests(unittest.TestCase):
    def test_offline_plan_creates_scene_prompts_and_continuity(self):
        request = StoryPlanRequest(idea="A missing phone rings from an abandoned house")
        plan = create_story_plan(request)
        self.assertEqual(plan["engine"], "offline_template")
        self.assertEqual(len(plan["scenes"]), 6)
        self.assertEqual(sum(s["duration_seconds"] for s in plan["scenes"]), 55)
        self.assertTrue(plan["scenes"][0]["image_prompt"])
        self.assertTrue(plan["scenes"][0]["video_prompt"])
        self.assertIn("character_notes", plan["scenes"][0]["continuity"])

    def test_custom_scene_count_and_duration_are_preserved(self):
        request = StoryPlanRequest(
            idea="A detective finds a clue in a railway station",
            target_duration_seconds=90,
            scene_count=8,
            language="Tamil",
            aspect_ratio="16:9",
        )
        plan = create_story_plan(request)
        self.assertEqual(len(plan["scenes"]), 8)
        self.assertEqual(sum(s["duration_seconds"] for s in plan["scenes"]), 90)
        self.assertEqual(plan["project"]["language"], "Tamil")
        self.assertEqual(plan["project"]["aspect_ratio"], "16:9")

    def test_blank_idea_is_rejected(self):
        with self.assertRaises(Exception):
            StoryPlanRequest(idea="        ")


if __name__ == "__main__":
    unittest.main()
