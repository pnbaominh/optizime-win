"""
Unit tests for core/contracts.py and core/registry_backup.py.
"""

import os
import unittest
import tempfile
import winreg
from unittest.mock import patch, MagicMock

from core.contracts import (
    TweakCategory,
    TweakState,
    RegistryRoot,
    RegistryValueType,
    RegistryTargetSpec,
    TweakDescriptor,
    RegistryBackupEntry,
    BackupSnapshot,
    RamStatusMetrics,
    TweakExecutionResult
)
from core.registry_backup import RegistryBackupService


class TestContracts(unittest.TestCase):
    def test_registry_target_spec_validation(self):
        # Valid spec
        spec = RegistryTargetSpec(
            root=RegistryRoot.HKLM,
            subkey="SYSTEM\\CurrentControlSet\\Control\\PriorityControl",
            value_name="Win32PrioritySeparation",
            value_type=RegistryValueType.REG_DWORD,
            optimized_value=0x26,
            default_value=0x02
        )
        spec.validate()

        # Invalid subkey with forward slash
        invalid_slash = RegistryTargetSpec(
            root=RegistryRoot.HKLM,
            subkey="SYSTEM/CurrentControlSet",
            value_name="Test",
            value_type=RegistryValueType.REG_DWORD,
            optimized_value=1,
            default_value=0
        )
        with self.assertRaises(ValueError):
            invalid_slash.validate()

        # Invalid subkey starting with backslash
        invalid_leading = RegistryTargetSpec(
            root=RegistryRoot.HKLM,
            subkey="\\SYSTEM\\CurrentControlSet",
            value_name="Test",
            value_type=RegistryValueType.REG_DWORD,
            optimized_value=1,
            default_value=0
        )
        with self.assertRaises(ValueError):
            invalid_leading.validate()

        # Out of bounds DWORD
        invalid_dword = RegistryTargetSpec(
            root=RegistryRoot.HKLM,
            subkey="SYSTEM\\CurrentControlSet",
            value_name="Test",
            value_type=RegistryValueType.REG_DWORD,
            optimized_value=0x1FFFFFFFF,
            default_value=0
        )
        with self.assertRaises(ValueError):
            invalid_dword.validate()

    def test_tweak_descriptor_validation(self):
        desc = TweakDescriptor(
            tweak_id="cpu_power_plan",
            category=TweakCategory.CPU,
            title="Ultimate Performance Power Plan",
            description="Kích hoạt power plan Ultimate Performance",
            requires_admin=True,
            requires_reboot=False
        )
        desc.validate()

        # Invalid id with space
        invalid_desc = TweakDescriptor(
            tweak_id="cpu power plan",
            category=TweakCategory.CPU,
            title="Title",
            description="Desc",
            requires_admin=True,
            requires_reboot=False
        )
        with self.assertRaises(ValueError):
            invalid_desc.validate()

    def test_registry_backup_entry_validation(self):
        entry_valid = RegistryBackupEntry(
            root=RegistryRoot.HKLM,
            subkey="SOFTWARE\\Policies",
            value_name="Key",
            value_type=4,
            previous_value=1,
            existed_before=True
        )
        entry_valid.validate()

        # existed_before=True but previous_value=None
        entry_invalid = RegistryBackupEntry(
            root=RegistryRoot.HKLM,
            subkey="SOFTWARE\\Policies",
            value_name="Key",
            value_type=4,
            previous_value=None,
            existed_before=True
        )
        with self.assertRaises(ValueError):
            entry_invalid.validate()

    def test_ram_status_metrics_validation(self):
        metrics = RamStatusMetrics(
            total_physical_kb=16000000,
            available_physical_kb=8000000,
            usage_percent=50.0,
            calculated_svchost_threshold_kb=16000000,
            standby_purge_active=False
        )
        metrics.validate()

        # Negative percent
        with self.assertRaises(ValueError):
            RamStatusMetrics(
                total_physical_kb=16000000,
                available_physical_kb=8000000,
                usage_percent=-5.0,
                calculated_svchost_threshold_kb=16000000,
                standby_purge_active=False
            ).validate()


class TestRegistryBackupService(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.service = RegistryBackupService(backup_dir=self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    def test_capture_entry_existing(self, mock_query, mock_open):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_query.return_value = (42, winreg.REG_DWORD)

        entry = self.service.capture_entry(
            RegistryRoot.HKLM,
            "SYSTEM\\CurrentControlSet\\Control\\PriorityControl",
            "Win32PrioritySeparation"
        )
        self.assertTrue(entry.existed_before)
        self.assertEqual(entry.previous_value, 42)
        self.assertEqual(entry.value_type, winreg.REG_DWORD)

    @patch("winreg.OpenKey", side_effect=FileNotFoundError)
    def test_capture_entry_non_existing(self, mock_open):
        entry = self.service.capture_entry(
            RegistryRoot.HKCU,
            "Software\\TestKey",
            "NonExistingValue"
        )
        self.assertFalse(entry.existed_before)
        self.assertIsNone(entry.previous_value)

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    def test_create_and_load_snapshot(self, mock_query, mock_open):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_query.return_value = (10, winreg.REG_DWORD)

        targets = [
            RegistryTargetSpec(
                root=RegistryRoot.HKLM,
                subkey="SYSTEM\\CurrentControlSet\\Control\\PriorityControl",
                value_name="Win32PrioritySeparation",
                value_type=RegistryValueType.REG_DWORD,
                optimized_value=0x26,
                default_value=0x02
            )
        ]

        snapshot = self.service.create_snapshot(
            category=TweakCategory.CPU,
            targets=targets,
            power_scheme_guid_before="381b4222-f694-41f0-9685-ff5bb260df2e"
        )
        self.assertIsNotNone(snapshot.snapshot_id)
        self.assertEqual(len(snapshot.entries), 1)

        # Load back
        loaded = self.service.load_snapshot(snapshot.snapshot_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.snapshot_id, snapshot.snapshot_id)
        self.assertEqual(loaded.power_scheme_guid_before, "381b4222-f694-41f0-9685-ff5bb260df2e")
        self.assertEqual(len(loaded.entries), 1)
        self.assertEqual(loaded.entries[0].previous_value, 10)

    @patch("winreg.CreateKeyEx")
    @patch("winreg.SetValueEx")
    @patch("winreg.OpenKey")
    @patch("winreg.DeleteValue")
    @patch("core.registry_backup.run_cmd")
    def test_restore_snapshot(self, mock_run, mock_del, mock_open, mock_set, mock_create):
        # Create a mock snapshot on disk
        entry1 = RegistryBackupEntry(
            root=RegistryRoot.HKLM,
            subkey="SYSTEM\\CurrentControlSet\\Control\\PriorityControl",
            value_name="Win32PrioritySeparation",
            value_type=4,
            previous_value=2,
            existed_before=True
        )
        entry2 = RegistryBackupEntry(
            root=RegistryRoot.HKLM,
            subkey="SYSTEM\\CurrentControlSet\\Control\\Power\\PowerThrottling",
            value_name="PowerThrottlingOff",
            value_type=4,
            previous_value=None,
            existed_before=False
        )
        snapshot = BackupSnapshot(
            snapshot_id="test_restore_snap",
            created_at_iso="2026-10-17T00:00:00Z",
            category=TweakCategory.CPU,
            entries=(entry1, entry2),
            power_scheme_guid_before="381b4222-f694-41f0-9685-ff5bb260df2e"
        )
        self.service._save_snapshot_to_disk(snapshot)

        mock_run.return_value = MagicMock(returncode=0)
        mock_create.return_value.__enter__.return_value = MagicMock()
        mock_open.return_value.__enter__.return_value = MagicMock()

        ok, msg = self.service.restore_snapshot("test_restore_snap")
        self.assertTrue(ok)
        self.assertIn("Đã khôi phục thành công", msg)
        mock_set.assert_called_once()
        mock_del.assert_called_once()
        mock_run.assert_called_once_with(["powercfg", "/setactive", "381b4222-f694-41f0-9685-ff5bb260df2e"], timeout=10)

    def test_snapshot_id_path_traversal_blocked(self):
        # Path traversal with relative paths or special chars should be rejected
        self.assertIsNone(self.service.load_snapshot("../evil_payload"))
        self.assertIsNone(self.service.load_snapshot("..\\evil_payload"))
        self.assertIsNone(self.service.load_snapshot("snap/id"))
        self.assertIsNone(self.service.load_snapshot("snap;rm -rf"))

    @patch("winreg.CreateKeyEx")
    @patch("winreg.SetValueEx")
    def test_unauthorized_target_in_snapshot_blocked(self, mock_set, mock_create):
        # A snapshot trying to write to Windows Run key (startup persistence attack)
        malicious_entry = RegistryBackupEntry(
            root=RegistryRoot.HKLM,
            subkey="SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
            value_name="EvilBackdoor",
            value_type=1,
            previous_value="calc.exe",
            existed_before=True
        )
        snapshot = BackupSnapshot(
            snapshot_id="malicious_snapshot",
            created_at_iso="2026-10-17T00:00:00Z",
            category=TweakCategory.CPU,
            entries=(malicious_entry,)
        )
        self.service._save_snapshot_to_disk(snapshot)

        ok, msg = self.service.restore_snapshot("malicious_snapshot")
        # Should not call SetValueEx on unauthorized target
        mock_set.assert_not_called()
        self.assertIn("Bỏ qua target không được cấp phép", msg)


if __name__ == "__main__":
    unittest.main()
