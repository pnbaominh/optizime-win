import unittest
from core.network_optimizer import (
    DNS_PROVIDERS,
    probe_dns_socket,
    benchmark_all_dns_parallel,
    get_active_adapter_info,
    measure_ping_rtt,
    get_network_optimization_status,
    flush_dns_cache
)

class TestNetworkOptimizer(unittest.TestCase):
    def test_dns_providers_structure(self):
        self.assertGreaterEqual(len(DNS_PROVIDERS), 8)
        for name, info in DNS_PROVIDERS.items():
            self.assertIn("primary", info, f"{name} missing primary")
            self.assertIn("secondary", info, f"{name} missing secondary")
            self.assertIn("desc", info, f"{name} missing desc")
            self.assertIn("badge", info, f"{name} missing badge")
            # Verify primary IP format (at least contains 3 dots)
            self.assertEqual(info["primary"].count("."), 3, f"{name} invalid IPv4 format")

    def test_probe_dns_socket_structure(self):
        # Query known public DNS 1.1.1.1 or 8.8.8.8
        rtt = probe_dns_socket("1.1.1.1", timeout=2.0)
        self.assertIsInstance(rtt, float)
        # Invalid / unreachable IP with short timeout should safely return -1.0
        rtt_invalid = probe_dns_socket("192.0.2.1", timeout=0.3)
        self.assertEqual(rtt_invalid, -1.0)

    def test_get_active_adapter_info(self):
        info = get_active_adapter_info()
        self.assertIn("name", info)
        self.assertIn("description", info)
        self.assertIn("ipv4", info)
        self.assertIn("gateway", info)
        self.assertIn("dns", info)
        self.assertIn("status", info)
        self.assertIn("is_wifi", info)
        self.assertIsInstance(info["is_wifi"], bool)

    def test_get_network_optimization_status(self):
        status = get_network_optimization_status()
        self.assertIn("nagle_disabled", status)
        self.assertIn("throttling_disabled", status)
        self.assertIn("qos_limit_removed", status)
        self.assertIn("dns_leak_protected", status)
        self.assertIn("dns_cache_optimized", status)
        self.assertIn("ipv6_disabled", status)
        for k, v in status.items():
            self.assertIsInstance(v, bool, f"Key {k} should be boolean")

    def test_measure_ping_rtt(self):
        rtt = measure_ping_rtt("1.1.1.1", timeout_sec=2)
        self.assertIsInstance(rtt, float)

    def test_flush_dns_cache(self):
        ok, msg = flush_dns_cache()
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(msg, str)
        self.assertTrue(ok)

    def test_benchmark_all_dns_parallel(self):
        # Callback tracker
        progress_counts = []
        def on_prog(c, t, p):
            progress_counts.append((c, t, p))

        results = benchmark_all_dns_parallel(progress_callback=on_prog)
        self.assertEqual(len(results), len(DNS_PROVIDERS))
        self.assertGreater(len(progress_counts), 0)
        
        # Verify result item schema
        for item in results:
            self.assertIn("name", item)
            self.assertIn("avg_ms", item)
            self.assertIn("min_ms", item)
            self.assertIn("max_ms", item)
            self.assertIn("jitter_ms", item)
            self.assertIn("is_online", item)

        # Check sorting: online items first, lowest avg_ms first
        online_items = [r for r in results if r["is_online"]]
        if len(online_items) >= 2:
            for i in range(len(online_items) - 1):
                self.assertLessEqual(online_items[i]["avg_ms"], online_items[i + 1]["avg_ms"])

if __name__ == "__main__":
    unittest.main()
