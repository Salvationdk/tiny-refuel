"""Offline regression tests for bounded, fair coordinate lookups."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

spec = importlib.util.spec_from_file_location('geocoding_scraper', Path(__file__).parents[1] / 'custom_components/tiny_refuel/scraper.py')
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)

class GeocodingTests(unittest.TestCase):
    def test_fair_budget_after_cache_and_duplicate_filtering(self):
        addresses = ['Cached'] + [f'A road {i}' for i in range(40)] + ['A road 0'] + [f'B road {i}' for i in range(40)]
        brands = ['A'] * 42 + ['B'] * 40
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps([{'lat': '55.6', 'lon': '12.1'}]).encode()
        errors = []
        with patch.object(scraper, 'load_json', return_value={'cached': {'lat': 55.0, 'lon': 12.0}}), patch.object(scraper, 'save_json'), patch.object(scraper.time, 'sleep'), patch.object(scraper.urllib.request, 'urlopen', return_value=response) as fetch:
            result = scraper.geocode_new(addresses, errors, brands)
        self.assertEqual(fetch.call_count, 30)
        self.assertEqual(sum(k.startswith('a road') for k in result), 15)
        self.assertEqual(sum(k.startswith('b road') for k in result), 15)
        self.assertEqual(errors, [])

    def test_recent_misses_are_skipped_and_failure_stops_requests(self):
        with patch.object(scraper, 'load_json', return_value={'missing': {'none': True, 'ts': int(scraper.time.time())}}), patch.object(scraper, 'save_json'), patch.object(scraper.time, 'sleep'), patch.object(scraper.urllib.request, 'urlopen', side_effect=OSError('offline')) as fetch:
            errors = []
            scraper.geocode_new(['Missing', 'New A', 'New B'], errors, ['A', 'A', 'B'])
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(len(errors), 1)

    def test_geocoding_reports_brand_and_current_address(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps([{'lat': '55.6', 'lon': '12.1'}]).encode()
        progress = []
        with patch.object(scraper, 'load_json', return_value={}), patch.object(scraper, 'save_json'), patch.object(scraper.time, 'sleep'), patch.object(scraper.urllib.request, 'urlopen', return_value=response):
            scraper.geocode_new(['Testvej 1, 1000 København'], [], ['OK'], progress.append)
        self.assertEqual(progress, [{
            'phase': 'geokodning', 'provider': 'OK',
            'station': 'Testvej 1, 1000 København', 'current': 1, 'total': 1,
        }])

if __name__ == '__main__':
    unittest.main()
