"""Regression tests for Issue #23: Q8/F24 endpoint and changed tariff HTML."""
import importlib.util
import json
from pathlib import Path
import urllib.error
import unittest
from unittest.mock import patch

module_file = Path(__file__).parents[1] / "custom_components/tiny_refuel/scraper.py"
spec = importlib.util.spec_from_file_location("q8_issue23_scraper", module_file)
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)

FUEL_RESPONSE = {
    "data": {"stationsPrices": [
        {"stationId": "8001", "stationName": "F24",
         "address": "Testvej 1 4000 Roskilde Danmark",
         "products": [
             {"productName": "GoEasy 95 E10", "price": 16.09,
              "priceChangeDate": "2026-11-09T10:00:00"},
             {"productName": "GoEasy Diesel", "price": 18.39}
         ]},
        {"stationId": "8200", "stationName": "Q8 Service",
         "address": "Andenvej 2 4000 Roskilde Danmark",
         "products": [
             {"productName": "GoEasy 95 E10", "price": 16.19},
             {"productName": "GoEasy Diesel", "price": 18.49}
         ]},
    ]},
    "success": True,
}

CHARGING_TABLE = """
<script>{"itemsRow":[{"text":"999 kr/kWh"}]}</script>
<table><tr><th>Produkt</th><th>Listepris</th></tr>
<tr><td>GoEasy</td><td>17,59 kr/L</td></tr></table>
<h2>Vores Ladepriser til elbil</h2>
<table class="w-full border-collapse"><thead><tr>
<th>Betalningsmiddel</th><th>Pris på lynlader 150 kW</th><th>Pris på 22 kW</th>
</tr></thead><tbody><tr>
<td>Q8 firmakort – Firma Plus EL</td><td> 4,39 kr/kWh </td><td>3,49 kr/kWh</td>
</tr><tr><td>Registrerede brugere i app</td>
<td>4,39 kr/kWh</td><td>3,49 kr/kWh</td></tr>
</tbody></table>
"""


class Q8Issue23Tests(unittest.TestCase):
    def test_shared_api_address_and_both_brands(self):
        self.assertEqual(scraper.F24_URLS, [
            "https://beta.q8.dk/Station/GetStationPrices?page=1&pageSize=2000"
        ])
        errors = []
        with patch.object(scraper, "get_text", return_value=json.dumps(FUEL_RESPONSE)) as get:
            stations, ok = scraper.fetch_f24q8(errors)
        self.assertTrue(ok)
        self.assertEqual(errors, [])
        self.assertEqual(len(stations), 2)
        self.assertEqual({station["brand"] for station in stations}, {"F24", "Q8"})
        self.assertEqual(stations[0]["p95"], 16.09)
        self.assertEqual(stations[1]["diesel"], 18.49)
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.args[0], scraper.F24_URLS[0])

    def test_removed_404_endpoint_does_not_retry(self):
        errors = []
        exception = urllib.error.HTTPError(scraper.F24_URLS[0], 404, "Not Found", {}, None)
        with patch.object(scraper, "get_text", side_effect=exception) as get:
            with patch.object(scraper.time, "sleep") as sleep:
                stations, ok = scraper.fetch_f24q8(errors)
        self.assertFalse(ok)
        self.assertEqual(stations, [])
        self.assertEqual(errors, [{"f24q8": "HTTP 404"}])
        get.assert_called_once()
        sleep.assert_not_called()

    def test_transient_failure_then_success(self):
        errors = []
        with patch.object(scraper, "get_text", side_effect=[TimeoutError("upstream"), json.dumps(FUEL_RESPONSE)]):
            with patch.object(scraper.time, "sleep") as sleep:
                stations, ok = scraper.fetch_f24q8(errors)
        self.assertTrue(ok)
        self.assertEqual(len(stations), 2)
        sleep.assert_called_once()
        self.assertEqual(errors, [])

    def test_rendered_business_table_keeps_columns_separate(self):
        result = scraper.parse_q8_el_tariffs(CHARGING_TABLE)
        self.assertEqual([row["kind"] for row in result], ["Lyn (150 kW)", "Normal (22 kW)"])
        self.assertEqual([row["kwh"] for row in result], [4.39, 3.49])
        self.assertTrue(all(row["source"] == "q8.dk" for row in result))

    def test_fetch_q8_tariffs_does_not_report_error_on_valid_html(self):
        errors = []
        with patch.object(scraper, "get_text", return_value=CHARGING_TABLE):
            rows = scraper.fetch_q8_el(errors)
        self.assertEqual(len(rows), 2)
        self.assertEqual(errors, [])

    def test_22kw_only_table_never_invents_150kw_price(self):
        page = "<table><tr><th>Betalingsmetode</th><th>Pris på 22kW</th></tr>" \
               "<tr><td>App</td><td>3,75 kr/kWh</td></tr></table>"
        errors = []
        with patch.object(scraper, "get_text", return_value=page):
            rows = scraper.fetch_q8_el(errors)
        self.assertEqual(rows, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("q8_el", errors[0])


if __name__ == "__main__":
    unittest.main()
