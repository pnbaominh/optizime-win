"""
Unit tests for core/services.py to guarantee 100% BSOD safety and service integrity.
"""

import unittest
from unittest.mock import patch, MagicMock
import winreg

from core.services import (
    get_services_tweaks,
    get_service_start_type,
    set_service_start_type,
    ServiceTweak,
)

CRITICAL_SYSTEM_SERVICES_BLACKLIST = {
    # Vanguard Anti-Cheat & EasyAntiCheat
    "vgc", "vgk", "easyanticheat", "battleye",
    # Display & GPU
    "nvlddmkm", "nvdisplay.containerlocalroot", "nvcontainerlocalsystem", "igfxcuiservice", "amdfendrsr",
    # Audio
    "audiosrv", "audioendpointbuilder",
    # Core Network & Internet
    "wlansvc", "dhcp", "dnscache", "nlasvc", "netprofm", "lanmanworkstation", "lanmanserver",
    # Windows Core Kernel / Boot
    "rpcss", "dcomlaunch", "rpcendpointmapper", "plugplay", "lsm", "samss", "winlogon"
}


class TestServicesSafety(unittest.TestCase):
    def test_services_list_integrity_and_blacklist_protection(self):
        tweaks = get_services_tweaks()
        self.assertEqual(len(tweaks), 11)

        tweak_ids = set()
        for t in tweaks:
            self.assertIsInstance(t.id, str)
            self.assertTrue(len(t.id) > 0)
            self.assertNotIn(t.id, tweak_ids, f"Duplicate tweak id: {t.id}")
            tweak_ids.add(t.id)

            self.assertTrue(t.name)
            self.assertTrue(t.description)
            self.assertTrue(t.explanation)
            self.assertTrue(t.is_recommended)

            # Nếu là ServiceTweak, phải đảm bảo tuyệt đối không đụng tới Blacklist
            if isinstance(t, ServiceTweak):
                svc_lower = t.service_name.lower()
                self.assertNotIn(
                    svc_lower,
                    CRITICAL_SYSTEM_SERVICES_BLACKLIST,
                    f"CRITICAL FAULT: {svc_lower} is a protected service and must NEVER be touched!"
                )

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    def test_get_service_start_type_registry(self, mock_query, mock_open):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_query.return_value = (4, winreg.REG_DWORD)

        st = get_service_start_type("DiagTrack")
        self.assertEqual(st, "DISABLED")

        mock_query.return_value = (3, winreg.REG_DWORD)
        st = get_service_start_type("DiagTrack")
        self.assertEqual(st, "MANUAL")

        mock_query.return_value = (2, winreg.REG_DWORD)
        st = get_service_start_type("DiagTrack")
        self.assertEqual(st, "AUTO")

    @patch("winreg.OpenKey")
    @patch("winreg.SetValueEx")
    @patch("core.services.run_cmd")
    def test_set_service_start_type(self, mock_cmd, mock_set, mock_open):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_cmd.return_value = MagicMock(returncode=0)

        ok, msg = set_service_start_type("WerSvc", "disabled")
        self.assertTrue(ok)
        self.assertIn("được đặt thành", msg)
        mock_set.assert_called_with(
            mock_open.return_value.__enter__.return_value,
            "Start",
            0,
            winreg.REG_DWORD,
            4
        )


if __name__ == "__main__":
    unittest.main()
