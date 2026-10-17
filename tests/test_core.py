import unittest
import sys
import io

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from core.sys_info import get_windows_version_info, is_admin, get_system_storage_stats
from core.safety import list_system_restore_points
from core.engine import OptimizerEngine
from core.cleaner import SAFE_BLOATWARE_LIST

class TestCoreModules(unittest.TestCase):
    def test_sys_info(self):
        info = get_windows_version_info()
        self.assertIn("os_name", info)
        self.assertIn(info["os_name"], ["Windows 10", "Windows 11"])
        self.assertIn("build_number", info)
        print(f"Detected: {info['full_name']} | IsAdmin: {is_admin()}")

    def test_storage_stats(self):
        stats = get_system_storage_stats()
        self.assertGreater(stats["total_gb"], 0)
        self.assertGreater(stats["free_gb"], 0)
        print(f"Drive C: Free {stats['free_gb']} GB / {stats['total_gb']} GB")

    def test_optimizer_engine_tweaks(self):
        engine = OptimizerEngine()
        tweaks = engine.get_all_tweaks()
        self.assertGreater(len(tweaks), 5)
        print(f"Total tweaks loaded: {len(tweaks)}")
        for t in tweaks:
            state = t.check()
            self.assertIsInstance(state, bool)
            print(f"[{t.category}] {t.name}: {'Applied' if state else 'Default'}")

    def test_bloatware_list(self):
        self.assertGreater(len(SAFE_BLOATWARE_LIST), 0)

    def test_process_utils_hidden(self):
        from core.process_utils import run_cmd
        res = run_cmd(["cmd.exe", "/c", "echo", "HELLO_HIDDEN_CMD"], timeout=5)
        self.assertEqual(res.returncode, 0)
        self.assertIn("HELLO_HIDDEN_CMD", res.stdout)

    def test_version_logic(self):
        from core.version import parse_version_tuple, is_newer_version
        self.assertEqual(parse_version_tuple("v1.0.0"), (1, 0, 0))
        self.assertEqual(parse_version_tuple("1.2.3.4"), (1, 2, 3, 4))
        self.assertTrue(is_newer_version("v1.1.0", "1.0.0"))
        self.assertTrue(is_newer_version("2.0.0", "1.9.9"))
        self.assertFalse(is_newer_version("1.0.0", "1.0.0"))
        self.assertFalse(is_newer_version("0.9.9", "1.0.0"))

    def test_startup_manager(self):
        from core.startup_manager import list_startup_items
        items = list_startup_items()
        self.assertIsInstance(items, list)

    def test_classic_context_menu_tweak(self):
        from core.performance import Win11ClassicContextMenuTweak
        tweak = Win11ClassicContextMenuTweak()
        self.assertEqual(tweak.id, "perf_win11_classic_context")
        state = tweak.check()
        self.assertIsInstance(state, bool)

    def test_process_utils_timeout_not_retried(self):
        import subprocess
        from unittest.mock import patch
        from core.process_utils import run_cmd
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["sleep"], timeout=1)):
            with self.assertRaises(subprocess.TimeoutExpired):
                run_cmd(["sleep"], timeout=1)

    def test_create_system_restore_point_sanitization(self):
        from unittest.mock import patch, MagicMock
        from core.safety import create_system_restore_point
        with patch("core.safety.run_cmd") as mock_cmd:
            mock_cmd.return_value = MagicMock(returncode=0)
            ok, msg = create_system_restore_point("Malicious'; Remove-Item C:\\ -Recurse #")
            self.assertTrue(ok)
            # Ensure dangerous characters (quotes, semicolons, backslashes) are sanitized to underscores
            called_cmd = mock_cmd.call_args[0][0]
            ps_str = called_cmd[-1]
            self.assertNotIn("';", ps_str)
            self.assertNotIn(" -Recurse", ps_str)
            self.assertIn("Malicious___", ps_str)

    def test_engine_apply_all_aborts_when_restore_point_fails(self):
        from unittest.mock import patch
        from core.engine import OptimizerEngine
        engine = OptimizerEngine()
        with patch("core.engine.create_system_restore_point", return_value=(False, "Failed to create restore point")):
            s_count, f_count = engine.apply_all_recommended(require_restore_point=True)
            # Must abort: 0 success
            self.assertEqual(s_count, 0)
            self.assertGreater(f_count, 0)


if __name__ == "__main__":
    unittest.main()

