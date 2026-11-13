import unittest
from generation_providers import GenerationRequest, MockGenerationProvider, submit_generation


class GenerationProviderTests(unittest.TestCase):
    def test_mock_provider_is_free_and_does_not_claim_to_generate_media(self):
        request = GenerationRequest(
            project_id="project-1",
            scene_id="scene-1",
            prompt="A cinematic rainy street at midnight",
        )
        result = submit_generation("image", request)
        self.assertEqual(result.provider, "mock")
        self.assertEqual(result.status, "mock")
        self.assertIn("no media was generated", result.error)
        self.assertEqual(result.estimated_cost, "₹0 (no external request)")
        self.assertTrue(result.creator_review_required)

    def test_mock_provider_supports_video_contract(self):
        request = GenerationRequest(
            project_id="project-1",
            scene_id="scene-2",
            prompt="A slow cinematic tracking shot through a rainy street",
            duration_seconds=5,
        )
        result = MockGenerationProvider().submit("video", request)
        self.assertEqual(result.media_type, "video")
        self.assertEqual(result.status, "mock")

    def test_request_validates_aspect_ratio_and_duration(self):
        with self.assertRaises(Exception):
            GenerationRequest(project_id="p", scene_id="s", prompt="A long enough prompt", aspect_ratio="4:3")
        with self.assertRaises(Exception):
            GenerationRequest(project_id="p", scene_id="s", prompt="A long enough prompt", duration_seconds=90)


if __name__ == "__main__":
    unittest.main()
