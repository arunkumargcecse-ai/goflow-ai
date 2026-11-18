import os
import tempfile
import unittest
from unittest.mock import patch

import gpu_budget


class GpuBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "GOFLOW_DATA_DIR": self.temp.name,
            "GOFLOW_COMFYUI_URL": "https://worker.example.test",
            "GOFLOW_GPU_MONTHLY_BUDGET_INR": "1000",
            "GOFLOW_GPU_HOURLY_RATE_INR": "60",
            "GOFLOW_GPU_JOB_MAX_MINUTES": "20",
        }, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_remote_job_reserves_worst_case_estimate(self):
        result = gpu_budget.reserve_remote_job("job-1")
        self.assertEqual(result["estimated_cost_inr"], 20.0)
        self.assertEqual(gpu_budget.budget_status()["estimated_reserved_inr"], 20.0)

    def test_monthly_cap_blocks_over_budget_submission(self):
        with patch.dict(os.environ, {"GOFLOW_GPU_MONTHLY_BUDGET_INR": "10"}):
            with self.assertRaisesRegex(RuntimeError, "budget limit reached"):
                gpu_budget.reserve_remote_job("job-2")

    def test_remote_worker_requires_hourly_rate(self):
        with patch.dict(os.environ, {"GOFLOW_GPU_HOURLY_RATE_INR": "0"}):
            with self.assertRaisesRegex(RuntimeError, "set GOFLOW_GPU_HOURLY_RATE_INR"):
                gpu_budget.reserve_remote_job("job-3")

    def test_local_comfyui_has_no_cloud_reservation(self):
        with patch.dict(os.environ, {"GOFLOW_COMFYUI_URL": "http://127.0.0.1:8188"}):
            result = gpu_budget.reserve_remote_job("local-job")
        self.assertFalse(result["budget_enforced"])
        self.assertEqual(result["estimated_cost_inr"], 0.0)


if __name__ == "__main__":
    unittest.main()
