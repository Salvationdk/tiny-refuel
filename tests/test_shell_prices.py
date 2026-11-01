"""Official Shell JSON prices, product identity and fallback behaviour."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('shell_scraper', Path(__file__).parents[1] / 'custom_components/tiny_refuel/scraper.py')
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)


def station():
    return {'stationId': 'D001', 'street': 'Testvej 1', 'postalCode': '4000', 'city': 'Roskilde',
            'coordinates': {'latitude': '55.64', 'longitude': '12.08'},
            'prices': [
                {'fuelType': 'Autobenzin', 'octane': '95', 'productName': 'Blyfri 95', 'price': '14.29', 'currency': 'DKK', 'lastUpdated': '2026-11-01T10:00:00'},
                {'fuelType': 'Autobenzin', 'octane': '98', 'productName': 'V-Power', 'price': '16.29', 'currency': 'DKK'},
                {'fuelType': 'Autodiesel', 'productName': 'FuelSave Diesel', 'price': '13.29', 'currency': 'DKK'},
                {'fuelType': 'Autodiesel', 'productName': 'V-Power Diesel', 'price': '15.29', 'currency': 'DKK'}]}


class ShellPriceTests(unittest.TestCase):
    def test_products_coordinates_and_source_identity(self):
        row = scraper.normalize_shell_prices([station()])[0]
        self.assertEqual((row['p95'], row['p100'], row['diesel']), (14.29, None, 13.29))
        self.assertEqual(row['alt'], {'V-Power (98 oktan)': 16.29, 'V-Power Diesel': 15.29})
        self.assertEqual((row['lat'], row['lon']), (55.64, 12.08))
        self.assertEqual(row['source'], 'shellservice.dk')
        self.assertEqual(row['location_id'], 'D001')

    def test_success_does_not_request_pdf(self):
        errors = []
        with patch.object(scraper, 'get_text', return_value=json.dumps([station()])) as request, patch.object(scraper, 'fetch_shell_pdf') as pdf:
            rows, ok = scraper.fetch_shell(errors)
        self.assertTrue(ok)
        self.assertEqual(len(rows), 1)
        self.assertEqual(errors, [])
        self.assertEqual(request.call_args.args[0], scraper.SHELL_PRICES_API)
        pdf.assert_not_called()

    def test_failure_uses_existing_fallback(self):
        errors = []
        with patch.object(scraper, 'get_text', return_value='not JSON'), patch.object(scraper, 'fetch_shell_pdf', return_value=([], False)) as pdf:
            self.assertEqual(scraper.fetch_shell(errors), ([], False))
        pdf.assert_called_once_with(errors)
        self.assertIn('shell_api', errors[0])

    def test_invalid_prices_are_not_zero_or_wrong_currency(self):
        item = station()
        for price in item['prices']:
            price['currency'] = 'EUR'
        with self.assertRaises(ValueError):
            scraper.normalize_shell_prices([item])
        item['prices'][0].update(currency='DKK', price='NaN')
        with self.assertRaises(ValueError):
            scraper.normalize_shell_prices([item])
        item['prices'][0].update(price='14.29', octane='100')
        row = scraper.normalize_shell_prices([item])[0]
        self.assertEqual(row['p100'], 14.29)
        self.assertIsNone(row['p95'])
