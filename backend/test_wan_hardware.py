import unittest

from wan_hardware import assess_wan_hardware


class WanHardwareAssessmentTests(unittest.TestCase):
    def test_integrated_or_cpu_only_worker_is_not_recommended(self):
        result = assess_wan_hardware([{"name": "Intel Iris Xe", "type": " xpu ",
                                       "vram_total_bytes": 1_000_000_000}])
        self.assertEqual(result["status"], "no_cuda_accelerator")
        self.assertFalse(result["execution_supported"])

    def test_cuda_below_planning_baseline_warns(self):
        result = assess_wan_hardware([{"name": "NVIDIA GPU", "type": "cuda",
                                       "vram_total_bytes": 16 * 1024 ** 3}])
        self.assertEqual(result["status"], "below_recommended_vram")
        self.assertEqual(result["max_reported_cuda_vram_bytes"], 16 * 1024 ** 3)

    def test_cuda_at_baseline_still_requires_real_test(self):
        result = assess_wan_hardware([{"name": "CUDA device", "type": "cuda",
                                       "vram_total_bytes": 24 * 1024 ** 3}])
        self.assertEqual(result["status"], "gpu_visible_review_required")
        self.assertFalse(result["execution_supported"])

    def test_malformed_devices_are_ignored(self):
        result = assess_wan_hardware([None, "not-a-device", {}])
        self.assertEqual(result["status"], "no_cuda_accelerator")
        self.assertEqual(len(result["accelerators"]), 1)


if __name__ == "__main__":
    unittest.main()
