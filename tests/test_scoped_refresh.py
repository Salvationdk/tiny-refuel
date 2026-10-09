"""Focused tests for partial fuel refreshes."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "tiny_refuel_scraper", Path(__file__).parents[1] / "custom_components/tiny_refuel/scraper.py")
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)
_preserve_unselected_fuels = scraper._preserve_unselected_fuels


class ScopedRefreshTests(unittest.TestCase):
    def test_diesel_refresh_keeps_cached_petrol_prices_and_history(self):
        previous = [
            {"brand": "Shell", "source": "shellservice.dk", "address": "Main Street 1",
             "p95": 15.2, "p100": 16.1, "diesel": 14.8,
             "h95": [["2026-10-01", 15.2]], "h100": [["2026-10-01", 16.1]]},
            {"brand": "Shell", "source": "shellservice.dk", "address": "Main Street 2",
             "p95": 15.4, "diesel": None},
        ]
        fresh = [{"brand": "Shell", "source": "shellservice.dk", "address": "Main Street 1",
                  "p95": 15.8, "p100": 16.5, "diesel": 14.9}]

        rows = _preserve_unselected_fuels(fresh, previous, {"diesel"})

        self.assertEqual(rows[0]["p95"], 15.2)
        self.assertEqual(rows[0]["p100"], 16.1)
        self.assertEqual(rows[0]["diesel"], 14.9)
        self.assertEqual(rows[0]["h95"], [["2026-10-01", 15.2]])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["address"], "Main Street 2")

    def test_petrol_refresh_keeps_cached_diesel_price(self):
        previous = [{"brand": "Q8", "source": "q8.example", "address": "Road 1",
                     "p95": 15, "diesel": 14}]
        fresh = [{"brand": "Q8", "source": "q8.example", "address": "Road 1",
                  "p95": 15.5, "diesel": 14.4}]

        rows = _preserve_unselected_fuels(fresh, previous, {"benzin"})

        self.assertEqual(rows[0]["p95"], 15.5)
        self.assertEqual(rows[0]["diesel"], 14)


if __name__ == "__main__":
    unittest.main()
