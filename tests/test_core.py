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

if __name__ == "__main__":
    unittest.main()
