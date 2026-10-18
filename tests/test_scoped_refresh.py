"""Focused tests for partial fuel refreshes."""
import importlib.util
from pathlib import Path
import unittest
import tempfile
from copy import deepcopy
from unittest.mock import patch

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

    def test_omitted_station_preserves_only_unselected_fuel(self):
        old = {"brand": "Q8", "source": "f24.dk", "address": "Road 1",
               "p95": 15, "p100": 16, "h95": [["2026-10-01", 15]], "diesel": 14}
        rows = _preserve_unselected_fuels([], [old], {"benzin"})
        self.assertEqual(rows[0]["diesel"], 14)
        for key in ("p95", "p100", "h95"):
            self.assertNotIn(key, rows[0])
        self.assertEqual(old["p95"], 15)

    def test_petrol_refresh_keeps_exact_ev_snapshot_and_stale_flag(self):
        station = {"brand": "Q8", "source": "f24.dk", "name": "Q8", "address": "Road 1",
                   "lat": 55.6, "lon": 12.5, "p95": 15, "diesel": 14, "kwh": 3}
        ev = [{"brand": "Q8", "name": "Q8", "address": "Road 1", "kwh": 3, "stale": True}]
        fuel = {"stations": [], "source_ok": {"f24.dk": False}, "unox_chargers": [], "ok_tariffs": []}
        electric = {"locations": [], "statuses": {}, "q8_tariffs": [], "circlek_tariffs": [], "eon_tariffs": [], "ionity_tariffs": []}
        with tempfile.TemporaryDirectory() as folder, patch.object(scraper, "OUT", str(Path(folder)/"out.json")), patch.object(scraper, "ADDRESS_CACHE", str(Path(folder)/"cache.json")), patch.object(scraper.fuel_providers, "collect", side_effect=lambda *args: deepcopy(fuel)), patch.object(scraper.electric_providers, "collect", return_value=electric), patch.object(scraper, "fetch_benefits", return_value=({}, [])):
            scraper.save_json(scraper.OUT, {"stations": [station], "ev": ev})
            scraper._collect(fuel_types=["benzin"])
            self.assertEqual(scraper.load_json(scraper.OUT, {})["ev"], ev)
            scraper._collect()
            generated = scraper.load_json(scraper.OUT, {})["ev"]
            self.assertEqual(len(generated), 1)
            self.assertTrue(generated[0]["stale"])
            self.assertEqual(generated[0]["source"], "f24.dk")


if __name__ == "__main__":
    unittest.main()
