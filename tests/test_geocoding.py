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


class CoordinateStatusTests(unittest.TestCase):
    def test_queue_separates_recent_misses_duplicates_and_missing_addresses(self):
        stations = [
            {'brand': 'A', 'address': 'Ready', 'lat': None},
            {'brand': 'B', 'address': 'Ready', 'lat': None},
            {'brand': 'A', 'address': 'Miss', 'lat': None},
            {'brand': 'A', 'address': 'Expired', 'lat': None},
            {'brand': 'A', 'address': '', 'lat': None},
            {'brand': 'A', 'liste': True, 'address': '', 'lat': None},
            {'brand': 'A', 'address': 'Found', 'lat': 55, 'lon': 12},
        ]
        cache = {'miss': {'none': True, 'ts': 999900}, 'expired': {'none': True, 'ts': 1}}
        status = scraper.coordinate_status(stations, cache, now=1000000)
        self.assertEqual(status['queued'], 2)
        self.assertEqual(status['not_found'], 1)
        self.assertEqual(status['missing_address'], 1)
        self.assertEqual(len(status['pending_addresses']), 3)
        miss = next(row for row in status['pending_addresses'] if row['address'] == 'Miss')
        self.assertIsNotNone(miss['retry_after'])
        ready = next(row for row in status['pending_addresses'] if row['address'] == 'Ready')
        self.assertIsNone(ready['retry_after'])

    def test_attempt_statistics_distinguish_success_no_match_and_failure(self):
        response = MagicMock()
        response.__enter__.return_value.read.side_effect = [b'[{"lat":"55", "lon":"12"}]', b'[]']
        stats, errors = {}, []
        with patch.object(scraper, 'load_json', return_value={}), patch.object(scraper, 'save_json'), patch.object(scraper.time, 'sleep'), patch.object(scraper.urllib.request, 'urlopen', side_effect=[response, response, OSError('offline')]):
            scraper.geocode_new(['Found', 'Not found', 'Failure'], errors, stats=stats)
        self.assertEqual(stats['attempted'], 3)
        self.assertEqual(stats['found'], 1)
        self.assertEqual(stats['not_found'], 1)
        self.assertEqual(stats['failed'], 1)
        self.assertEqual(stats['error'], 'offline')

    def test_partial_cached_coordinate_does_not_block_a_new_lookup(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'[{"lat":"55", "lon":"12"}]'
        with patch.object(scraper, 'load_json', return_value={'partial': {'lat': 55, 'ts': 9999999999}}), patch.object(scraper, 'save_json'), patch.object(scraper.time, 'sleep'), patch.object(scraper.urllib.request, 'urlopen', return_value=response) as get:
            result = scraper.geocode_new(['Partial'], [])
        self.assertEqual(get.call_count, 1)
        self.assertEqual(result['partial']['lon'], 12)
