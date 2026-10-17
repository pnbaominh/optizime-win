"""
Unit tests for core/gpu_optimizer.py (Isolated with unittest.mock).
"""

import unittest
import tempfile
import winreg
from unittest.mock import patch, MagicMock

from core.contracts import TweakCategory, TweakState
from core.registry_backup import RegistryBackupService
from core.gpu_optimizer import GpuOptimizerService


class TestGpuOptimizer(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.backup_service = RegistryBackupService(backup_dir=self.tmp_dir.name)
        self.service = GpuOptimizerService(backup_service=self.backup_service)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_descriptors_integrity(self):
        descriptors = self.service.get_descriptors()
        self.assertEqual(len(descriptors), 5)
        ids = [d.tweak_id for d in descriptors]
        self.assertIn("gpu_hags", ids)
        self.assertIn("gpu_vrr", ids)
        self.assertIn("gpu_game_mode", ids)
        self.assertIn("gpu_priority_dwm_flush", ids)
        self.assertIn("gpu_high_performance_preference", ids)
        for d in descriptors:
            self.assertEqual(d.category, TweakCategory.GPU)

    @patch.object(GpuOptimizerService, "is_admin", return_value=True)
    @patch("winreg.CreateKeyEx")
    @patch("winreg.SetValueEx")
    def test_hags_lifecycle(self, mock_set, mock_create, mock_admin):
        mock_create.return_value.__enter__.return_value = MagicMock()

        res_apply = self.service.apply_tweak("gpu_hags")
        self.assertTrue(res_apply.success)
        self.assertEqual(res_apply.new_state, TweakState.OPTIMIZED)
        self.assertTrue(res_apply.requires_reboot)

        # Status check optimized
        with patch("winreg.OpenKey") as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            with patch("winreg.QueryValueEx", return_value=(2, winreg.REG_DWORD)):
                self.assertEqual(self.service.get_status("gpu_hags"), TweakState.OPTIMIZED)

            # Revert
            res_revert = self.service.revert_tweak("gpu_hags")
            self.assertTrue(res_revert.success)
            self.assertEqual(res_revert.new_state, TweakState.DEFAULT)
            self.assertTrue(res_revert.requires_reboot)

    @patch("winreg.CreateKey")
    @patch("winreg.SetValueEx")
    @patch("winreg.QueryValueEx")
    def test_vrr_lifecycle(self, mock_query, mock_set, mock_create):
        mock_create.return_value.__enter__.return_value = MagicMock()
        mock_query.return_value = ("OtherSetting=0;", winreg.REG_SZ)

        res_apply = self.service.apply_tweak("gpu_vrr")
        self.assertTrue(res_apply.success)
        self.assertEqual(res_apply.new_state, TweakState.OPTIMIZED)

        # Verify appended or replaced
        mock_set.assert_called_with(
            mock_create.return_value.__enter__.return_value,
            "DirectXUserGlobalSettings",
            0,
            winreg.REG_SZ,
            "OtherSetting=0;VRROptimizeEnable=1;"
        )

        # Revert
        mock_query.return_value = ("OtherSetting=0;VRROptimizeEnable=1;", winreg.REG_SZ)
        res_revert = self.service.revert_tweak("gpu_vrr")
        self.assertTrue(res_revert.success)
        self.assertEqual(res_revert.new_state, TweakState.DEFAULT)
        mock_set.assert_called_with(
            mock_create.return_value.__enter__.return_value,
            "DirectXUserGlobalSettings",
            0,
            winreg.REG_SZ,
            "OtherSetting=0;VRROptimizeEnable=0;"
        )

    @patch("winreg.CreateKeyEx")
    @patch("winreg.SetValueEx")
    def test_game_mode_lifecycle(self, mock_set, mock_create):
        mock_create.return_value.__enter__.return_value = MagicMock()

        res = self.service.apply_tweak("gpu_game_mode")
        self.assertTrue(res.success)
        self.assertEqual(res.new_state, TweakState.OPTIMIZED)

        with patch("winreg.OpenKey") as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            res_revert = self.service.revert_tweak("gpu_game_mode")
            self.assertTrue(res_revert.success)
            self.assertEqual(res_revert.new_state, TweakState.DEFAULT)

    @patch("winreg.CreateKey")
    @patch("winreg.SetValueEx")
    def test_high_performance_gpu_preference(self, mock_set, mock_create):
        mock_create.return_value.__enter__.return_value = MagicMock()

        res = self.service.apply_tweak("gpu_high_performance_preference")
        self.assertTrue(res.success)
        self.assertEqual(res.new_state, TweakState.OPTIMIZED)
        mock_set.assert_called_with(
            mock_create.return_value.__enter__.return_value,
            "DefaultGpuPreference",
            0,
            winreg.REG_DWORD,
            2
        )

        with patch("winreg.OpenKey") as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            with patch("winreg.DeleteValue") as mock_del:
                res_revert = self.service.revert_tweak("gpu_high_performance_preference")
                self.assertTrue(res_revert.success)
                self.assertEqual(res_revert.new_state, TweakState.DEFAULT)
                mock_del.assert_called_once()

    @patch.object(GpuOptimizerService, "is_admin", return_value=True)
    @patch("winreg.CreateKeyEx")
    @patch("winreg.CreateKey")
    @patch("winreg.SetValueEx")
    @patch("winreg.QueryValueEx", return_value=("", winreg.REG_SZ))
    def test_quick_apply_and_revert_all(self, mock_query, mock_set, mock_create, mock_create_ex, mock_admin):
        mock_create.return_value.__enter__.return_value = MagicMock()
        mock_create_ex.return_value.__enter__.return_value = MagicMock()

        results_apply = self.service.quick_apply_all()
        self.assertEqual(len(results_apply), 5)
        for res in results_apply.values():
            self.assertTrue(res.success)

        with patch("winreg.OpenKey") as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            with patch("winreg.DeleteValue"):
                results_revert = self.service.revert_all()
                self.assertEqual(len(results_revert), 5)
                for res in results_revert.values():
                    self.assertTrue(res.success)


if __name__ == "__main__":
    unittest.main()
