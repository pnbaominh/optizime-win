"""
Integration test suite for Windows Deep Optimizer v1.2.0:
- End-to-end workflow: Backup -> Quick Apply -> Verify Snapshots -> Revert/Restore
- Mandatory Zero-Disk Storage Constraint Audit (test_zero_disk_storage_constraint)
"""

import os
import unittest
import tempfile
import winreg
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.contracts import TweakCategory, TweakState
from core.registry_backup import RegistryBackupService
from core.cpu_optimizer import CpuOptimizerService
from core.gpu_optimizer import GpuOptimizerService
from core.ram_optimizer import (
    set_disable_paging_executive,
    apply_svchost_split_threshold,
    AutoStandbyPurgeWorker
)


class TestIntegrationWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.backup_service = RegistryBackupService(backup_dir=self.tmp_dir.name)
        self.cpu_service = CpuOptimizerService(backup_service=self.backup_service)
        self.gpu_service = GpuOptimizerService(backup_service=self.backup_service)

    def tearDown(self):
        self.tmp_dir.cleanup()

    @patch.object(CpuOptimizerService, "is_admin", return_value=True)
    @patch.object(GpuOptimizerService, "is_admin", return_value=True)
    @patch("winreg.CreateKeyEx")
    @patch("winreg.CreateKey")
    @patch("winreg.SetValueEx")
    @patch("winreg.QueryValueEx", return_value=(0, winreg.REG_DWORD))
    @patch("core.cpu_optimizer.run_cmd")
    def test_end_to_end_quick_apply_and_backup_restore(
        self,
        mock_cmd,
        mock_query,
        mock_set,
        mock_create,
        mock_create_ex,
        mock_gpu_admin,
        mock_cpu_admin
    ):
        mock_create.return_value.__enter__.return_value = MagicMock()
        mock_create_ex.return_value.__enter__.return_value = MagicMock()
        mock_cmd.return_value = MagicMock(returncode=0, stdout="Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e")

        # 1. Quick Apply CPU
        cpu_results = self.cpu_service.quick_apply_all()
        self.assertEqual(len(cpu_results), 5)
        for tid, res in cpu_results.items():
            self.assertTrue(res.success, f"CPU tweak {tid} failed: {res.message}")

        # 2. Quick Apply GPU
        gpu_results = self.gpu_service.quick_apply_all()
        self.assertEqual(len(gpu_results), 5)
        for tid, res in gpu_results.items():
            self.assertTrue(res.success, f"GPU tweak {tid} failed: {res.message}")

        # 3. Verify backup snapshots generated on disk
        cpu_snaps = self.backup_service.list_snapshots(TweakCategory.CPU)
        gpu_snaps = self.backup_service.list_snapshots(TweakCategory.GPU)
        self.assertGreater(len(cpu_snaps), 0)
        self.assertGreater(len(gpu_snaps), 0)

        # 4. Restore from backup
        with patch("winreg.OpenKey") as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            with patch("winreg.DeleteValue"):
                ok_cpu, msg_cpu = self.backup_service.restore_latest_by_category(TweakCategory.CPU)
                self.assertTrue(ok_cpu)

                ok_gpu, msg_gpu = self.backup_service.restore_latest_by_category(TweakCategory.GPU)
                self.assertTrue(ok_gpu)

    def test_zero_disk_storage_constraint(self):
        """
        Kiểm toán bắt buộc: Tuyệt đối không chứa bất kỳ từ khóa hay thao tác nào
        liên quan đến ổ đĩa (defrag, cleanmgr, fsutil, trim, diskpart, DisableDeleteNotification, NtfsDisableLastAccessUpdate).
        """
        forbidden_tokens = [
            "defrag",
            "cleanmgr",
            "fsutil",
            "disabledeletenotification",
            "ntfsdisablelastaccessupdate",
            "trimdrive",
            "optimizedrive",
            "chkdsk",
            "diskpart",
            "clearpagefileatshutdown"  # Tránh can thiệp disk swap tại shutdown
        ]

        target_files = [
            "core/cpu_optimizer.py",
            "core/gpu_optimizer.py",
            "core/ram_optimizer.py",
            "core/contracts.py",
            "core/registry_backup.py",
            "ui/cpu_gpu_tab.py"
        ]

        base_dir = Path(__file__).resolve().parent.parent

        for rel_path in target_files:
            file_path = base_dir / rel_path
            self.assertTrue(file_path.exists(), f"Tệp không tồn tại: {rel_path}")

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().lower()

            for token in forbidden_tokens:
                self.assertNotIn(
                    token,
                    content,
                    f"VI PHẠM QUY TẮC ZERO-DISK: Tìm thấy từ khóa cấm '{token}' trong tệp {rel_path}!"
                )


if __name__ == "__main__":
    unittest.main()
