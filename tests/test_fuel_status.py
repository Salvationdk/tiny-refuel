"""Offline regression tests for per-source fuel data status."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "fuel_status_scraper", Path(__file__).parents[1] / "custom_components/tiny_refuel/scraper.py")
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)


class FuelStatusTests(unittest.TestCase):
    def test_keeps_last_success_and_counts_missing_coordinates(self):
        stations = [
            {"brand": "Circle K", "source": "api.circlek.com", "address": "A vej 1", "lat": None, "lon": None, "p95": 15.5},
            {"brand": "Circle K", "source": "api.circlek.com", "address": "B vej 2", "lat": 55.6, "lon": 12.1, "diesel": 14.2},
        ]
        previous = {"api.circlek.com": {"last_success": "2026-10-09T10:00:00Z"}}
        statuses = scraper._fuel_source_statuses(
            {"api.circlek.com": False, "goon.nu": True}, stations, previous,
            [{"ck_api": "offline"}], "2026-10-10T10:00:00Z")
        failed = statuses["api.circlek.com"]
        self.assertEqual(failed["status"], "stale")
        self.assertEqual(failed["last_success"], "2026-10-09T10:00:00Z")
        self.assertEqual(failed["records"], 2)
        self.assertEqual(failed["priced"], 2)
        self.assertEqual(failed["missing_coordinates"], 1)
        self.assertEqual(failed["error"], "offline")
        self.assertEqual(statuses["goon.nu"]["status"], "ok")
        self.assertEqual(statuses["goon.nu"]["last_success"], "2026-10-10T10:00:00Z")


if __name__ == "__main__":
    unittest.main()
