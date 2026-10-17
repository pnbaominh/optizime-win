"""
Unit tests for core/cpu_optimizer.py (Isolated with unittest.mock).
"""

import unittest
import tempfile
import winreg
from unittest.mock import patch, MagicMock

from core.contracts import TweakCategory, TweakState
from core.registry_backup import RegistryBackupService
from core.cpu_optimizer import CpuOptimizerService, ULTIMATE_PERF_BASE_GUID, BALANCED_SCHEME_GUID


class TestCpuOptimizer(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.backup_service = RegistryBackupService(backup_dir=self.tmp_dir.name)
        self.service = CpuOptimizerService(backup_service=self.backup_service)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_descriptors_integrity(self):
        descriptors = self.service.get_descriptors()
        self.assertEqual(len(descriptors), 6)
        ids = [d.tweak_id for d in descriptors]
        self.assertIn("cpu_ultimate_power_plan", ids)
        self.assertIn("cpu_win32_priority_separation", ids)
        self.assertIn("cpu_core_unparking", ids)
        self.assertIn("cpu_mmcss_responsiveness", ids)
        self.assertIn("cpu_disable_power_throttling", ids)
        self.assertIn("cpu_global_timer_resolution", ids)
        for d in descriptors:
            self.assertEqual(d.category, TweakCategory.CPU)

    @patch.object(CpuOptimizerService, "is_admin", return_value=False)
    def test_apply_without_admin(self, mock_admin):
        res = self.service.apply_tweak("cpu_win32_priority_separation")
        self.assertFalse(res.success)
        self.assertEqual(res.new_state, TweakState.ERROR)
        self.assertIn("Administrator", res.message)

    @patch.object(CpuOptimizerService, "is_admin", return_value=True)
    @patch("winreg.CreateKeyEx")
    @patch("winreg.SetValueEx")
    def test_apply_and_revert_win32_priority(self, mock_set, mock_create, mock_admin):
        mock_create.return_value.__enter__.return_value = MagicMock()

        # Apply
        res_apply = self.service.apply_tweak("cpu_win32_priority_separation")
        self.assertTrue(res_apply.success)
        self.assertEqual(res_apply.new_state, TweakState.OPTIMIZED)
        mock_set.assert_called_with(
            mock_create.return_value.__enter__.return_value,
            "Win32PrioritySeparation",
            0,
            winreg.REG_DWORD,
            0x26
        )

        # Revert
        with patch("winreg.OpenKey") as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            res_revert = self.service.revert_tweak("cpu_win32_priority_separation")
            self.assertTrue(res_revert.success)
            self.assertEqual(res_revert.new_state, TweakState.DEFAULT)
            mock_set.assert_called_with(
                mock_open.return_value.__enter__.return_value,
                "Win32PrioritySeparation",
                0,
                winreg.REG_DWORD,
                0x02
            )

    @patch.object(CpuOptimizerService, "is_admin", return_value=True)
    @patch("core.cpu_optimizer.run_cmd")
    def test_ultimate_power_plan_lifecycle(self, mock_cmd, mock_admin):
        # 1. Check status default
        mock_cmd.return_value = MagicMock(returncode=0, stdout=f"Power Scheme GUID: {BALANCED_SCHEME_GUID} (Balanced)")
        status = self.service.get_status("cpu_ultimate_power_plan")
        self.assertEqual(status, TweakState.DEFAULT)

        # 2. Apply: list returns existing ultimate scheme
        def cmd_side_effect(cmd, **kwargs):
            if "/getactivescheme" in cmd:
                return MagicMock(returncode=0, stdout=f"Power Scheme GUID: {BALANCED_SCHEME_GUID} (Balanced)")
            elif "/list" in cmd:
                return MagicMock(returncode=0, stdout=f"Power Scheme GUID: {ULTIMATE_PERF_BASE_GUID}  (Ultimate Performance)")
            elif "/setactive" in cmd:
                return MagicMock(returncode=0, stdout="")
            return MagicMock(returncode=0, stdout="")

        mock_cmd.side_effect = cmd_side_effect
        res_apply = self.service.apply_tweak("cpu_ultimate_power_plan")
        self.assertTrue(res_apply.success)
        self.assertEqual(res_apply.new_state, TweakState.OPTIMIZED)

        # 3. Check status optimized
        mock_cmd.side_effect = None
        mock_cmd.return_value = MagicMock(returncode=0, stdout=f"Power Scheme GUID: {ULTIMATE_PERF_BASE_GUID} (Ultimate Performance)")
        status_opt = self.service.get_status("cpu_ultimate_power_plan")
        self.assertEqual(status_opt, TweakState.OPTIMIZED)

        # 4. Revert
        mock_cmd.return_value = MagicMock(returncode=0, stdout="")
        res_revert = self.service.revert_tweak("cpu_ultimate_power_plan")
        self.assertTrue(res_revert.success)
        self.assertEqual(res_revert.new_state, TweakState.DEFAULT)

    @patch.object(CpuOptimizerService, "is_admin", return_value=True)
    @patch("core.cpu_optimizer.run_cmd")
    def test_core_unparking_lifecycle(self, mock_cmd, mock_admin):
        # Mock powercfg query returning OEM initial values (AC: 10%, DC: 20%)
        def mock_run_fn(cmd, **kwargs):
            if "/q" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="Current AC Power Setting Index: 0x0000000a\nCurrent DC Power Setting Index: 0x00000014"
                )
            return MagicMock(returncode=0, stdout="")

        mock_cmd.side_effect = mock_run_fn
        res_apply = self.service.apply_tweak("cpu_core_unparking")
        self.assertTrue(res_apply.success)
        self.assertEqual(res_apply.new_state, TweakState.OPTIMIZED)

        # Status check
        mock_cmd.side_effect = None
        mock_cmd.return_value = MagicMock(returncode=0, stdout="Current AC Power Setting Index: 0x00000064")
        self.assertEqual(self.service.get_status("cpu_core_unparking"), TweakState.OPTIMIZED)

        # Revert: should restore original OEM values (10 and 20)
        captured_cmds = []
        def mock_revert_fn(cmd, **kwargs):
            captured_cmds.append(cmd)
            return MagicMock(returncode=0, stdout="")

        mock_cmd.side_effect = mock_revert_fn
        res_revert = self.service.revert_tweak("cpu_core_unparking")
        self.assertTrue(res_revert.success)
        self.assertEqual(res_revert.new_state, TweakState.DEFAULT)
        # Verify 10 and 20 were passed back
        ac_cmd = [c for c in captured_cmds if "-setacvalueindex" in c][0]
        dc_cmd = [c for c in captured_cmds if "-setdcvalueindex" in c][0]
        self.assertEqual(ac_cmd[-1], "10")
        self.assertEqual(dc_cmd[-1], "20")

    @patch.object(CpuOptimizerService, "is_admin", return_value=True)
    @patch("winreg.CreateKeyEx")
    @patch("winreg.SetValueEx")
    @patch("core.cpu_optimizer.run_cmd")
    def test_quick_apply_and_revert_all(self, mock_cmd, mock_set, mock_create, mock_admin):
        mock_create.return_value.__enter__.return_value = MagicMock()
        mock_cmd.return_value = MagicMock(returncode=0, stdout=f"Power Scheme GUID: {BALANCED_SCHEME_GUID}")

        results_apply = self.service.quick_apply_all()
        self.assertEqual(len(results_apply), 6)
        for res in results_apply.values():
            self.assertTrue(res.success)

        with patch("winreg.OpenKey") as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            results_revert = self.service.revert_all()
            self.assertEqual(len(results_revert), 6)
            for res in results_revert.values():
                self.assertTrue(res.success)


if __name__ == "__main__":
    unittest.main()
