import unittest
from core.memory_optimizer import (
    get_detailed_memory_info,
    trim_all_working_sets,
    get_boot_memory_status
)

class TestMemoryOptimizer(unittest.TestCase):
    def test_get_detailed_memory_info(self):
        info = get_detailed_memory_info()
        self.assertIn("total_mb", info)
        self.assertIn("avail_mb", info)
        self.assertIn("used_mb", info)
        self.assertIn("percent_used", info)
        self.assertGreater(info["total_mb"], 0)
        self.assertGreaterEqual(info["avail_mb"], 0)
        self.assertGreaterEqual(info["percent_used"], 0)
        self.assertLessEqual(info["percent_used"], 100)

    def test_trim_all_working_sets(self):
        ok, msg, count, freed = trim_all_working_sets()
        self.assertTrue(ok)
        self.assertIsInstance(msg, str)
        self.assertGreaterEqual(count, 1)
        self.assertGreaterEqual(freed, 0)

    def test_get_boot_memory_status(self):
        status = get_boot_memory_status()
        self.assertIn("sysmain_disabled", status)
        self.assertIn("memory_compression_disabled", status)
        self.assertIn("large_system_cache_app_mode", status)

    def test_full_memory_purge_evaluation(self):
        from unittest.mock import patch
        from core.memory_optimizer import full_memory_purge

        # Case 1: Both fail
        with patch("core.memory_optimizer.trim_all_working_sets", return_value=(False, "Failed trim", 0, 0)), \
             patch("core.memory_optimizer.purge_standby_list", return_value=(False, "Failed standby", 0)):
            ok, msg, freed = full_memory_purge()
            self.assertFalse(ok)
            self.assertIn("Thất bại", msg)

        # Case 2: Partial success (trim ok, standby failed)
        with patch("core.memory_optimizer.trim_all_working_sets", return_value=(True, "Trimmed", 15, 50)), \
             patch("core.memory_optimizer.purge_standby_list", return_value=(False, "Failed standby", 0)):
            ok, msg, freed = full_memory_purge()
            self.assertTrue(ok)
            self.assertIn("hoàn tất một phần", msg)


if __name__ == "__main__":
    unittest.main()
