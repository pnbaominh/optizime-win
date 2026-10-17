"""
Unit tests for core/ram_optimizer.py upgrades and AutoStandbyPurgeWorker.
"""

import unittest
import tempfile
import winreg
from unittest.mock import patch, MagicMock

from core.ram_optimizer import (
    set_disable_paging_executive,
    get_disable_paging_executive,
    apply_svchost_split_threshold,
    get_svchost_split_status,
    get_total_physical_ram_kb,
    AutoStandbyPurgeWorker,
    WINDOWS_DEFAULT_SVCHOST_SPLIT_KB
)
from core.registry_backup import RegistryBackupService


class TestRamOptimizerUpgrade(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.backup_service = RegistryBackupService(backup_dir=self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    @patch("winreg.QueryValueEx", return_value=(0, winreg.REG_DWORD))
    @patch("winreg.OpenKey")
    @patch("winreg.SetValueEx")
    def test_disable_paging_executive(self, mock_set, mock_open, mock_query):
        mock_open.return_value.__enter__.return_value = MagicMock()

        # Enable
        ok, msg = set_disable_paging_executive(True, self.backup_service)
        self.assertTrue(ok)
        self.assertIn("DisablePagingExecutive = 1", msg)
        mock_set.assert_called_with(
            mock_open.return_value.__enter__.return_value,
            "DisablePagingExecutive",
            0,
            winreg.REG_DWORD,
            1
        )

        # Disable
        ok2, msg2 = set_disable_paging_executive(False, self.backup_service)
        self.assertTrue(ok2)
        mock_set.assert_called_with(
            mock_open.return_value.__enter__.return_value,
            "DisablePagingExecutive",
            0,
            winreg.REG_DWORD,
            0
        )

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    def test_get_disable_paging_executive(self, mock_query, mock_open):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_query.return_value = (1, winreg.REG_DWORD)
        self.assertTrue(get_disable_paging_executive())

        mock_query.return_value = (0, winreg.REG_DWORD)
        self.assertFalse(get_disable_paging_executive())

    @patch("core.ram_optimizer.get_total_physical_ram_kb", return_value=16777216)
    @patch("winreg.QueryValueEx", return_value=(WINDOWS_DEFAULT_SVCHOST_SPLIT_KB, winreg.REG_DWORD))
    @patch("winreg.OpenKey")
    @patch("winreg.SetValueEx")
    def test_svchost_split_threshold(self, mock_set, mock_open, mock_query, mock_ram):
        mock_open.return_value.__enter__.return_value = MagicMock()

        # Apply
        ok, msg = apply_svchost_split_threshold(True, self.backup_service)
        self.assertTrue(ok)
        self.assertIn("16777216 KB", msg)
        mock_set.assert_called_with(
            mock_open.return_value.__enter__.return_value,
            "SvcHostSplitThresholdInKB",
            0,
            winreg.REG_DWORD,
            16777216
        )

        # Revert
        ok2, msg2 = apply_svchost_split_threshold(False, self.backup_service)
        self.assertTrue(ok2)
        self.assertIn(str(WINDOWS_DEFAULT_SVCHOST_SPLIT_KB), msg2)
        mock_set.assert_called_with(
            mock_open.return_value.__enter__.return_value,
            "SvcHostSplitThresholdInKB",
            0,
            winreg.REG_DWORD,
            WINDOWS_DEFAULT_SVCHOST_SPLIT_KB
        )

    @patch("core.ram_optimizer.purge_standby_list", return_value=(True, "Purged", 500))
    @patch("core.ram_optimizer.get_detailed_memory_info")
    def test_auto_standby_purge_worker(self, mock_mem, mock_purge):
        mock_mem.return_value = {
            "total_mb": 16384,
            "avail_mb": 2048,
            "used_mb": 14336,
            "percent_used": 87  # > 80%
        }

        worker = AutoStandbyPurgeWorker(check_interval_sec=0.05, usage_threshold_pct=80.0, cooldown_sec=10.0)
        self.assertFalse(worker.is_running())

        started = worker.start()
        self.assertTrue(started)
        self.assertTrue(worker.is_running())

        # Cho luồng chạy 1 chu kỳ
        import time
        time.sleep(0.15)

        self.assertGreaterEqual(worker.purge_count, 1)
        self.assertIsNotNone(worker.last_purge_iso)
        self.assertGreaterEqual(worker.total_freed_mb, 500)

        # Test cooldown: next check within cooldown shouldn't increment purge_count
        count_before = worker.purge_count
        time.sleep(0.1)
        self.assertEqual(worker.purge_count, count_before)

        # Get metrics
        metrics = worker.get_metrics()
        self.assertGreater(metrics.total_physical_kb, 0)
        self.assertEqual(metrics.usage_percent, 87.0)
        self.assertTrue(metrics.standby_purge_active)

        # Stop
        stopped = worker.stop()
        self.assertTrue(stopped)
        self.assertFalse(worker.is_running())


if __name__ == "__main__":
    unittest.main()
