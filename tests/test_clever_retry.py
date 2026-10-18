"""Clever must bypass a cached invalid response without accepting partial data."""
import http.client
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

spec = importlib.util.spec_from_file_location('clever_retry_scraper', Path(__file__).parents[1] / 'custom_components/tiny_refuel/scraper.py')
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)


class CleverRetryTests(unittest.TestCase):
    def test_valid_feed_is_fetched_only_once(self):
        payload = {'locations': [{'locationId': 'new'}]}
        with patch.object(scraper, 'get_text', return_value=json.dumps(payload)) as request:
            self.assertEqual(scraper.load_clever_locations(), payload)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.args[0], scraper.CLEVER_LOCATIONS_URL)
        self.assertEqual(request.call_args.kwargs['headers']['Accept-Encoding'], 'identity')

    def test_retry_has_distinct_url_preserves_query_and_uses_longer_timeout(self):
        with patch.object(scraper, 'CLEVER_LOCATIONS_URL', 'https://clever.dk/api/v2/chargers/locations?existing=1'), \
             patch.object(scraper.time, 'time_ns', return_value=123456789), \
             patch.object(scraper, 'get_text', side_effect=['{"locations":[', '{"locations":[]}']) as request:
            self.assertEqual(scraper.load_clever_locations(), {'locations': []})
        self.assertEqual(request.call_count, 2)
        first, retry = request.call_args_list
        self.assertNotEqual(first.args[0], retry.args[0])
        url = urlsplit(retry.args[0])
        self.assertEqual(url.hostname, 'clever.dk')
        self.assertEqual(parse_qs(url.query), {'existing': ['1'], '_tiny_refuel_retry': ['123456789']})
        self.assertEqual(retry.kwargs['headers']['Cache-Control'], 'no-cache')
        self.assertGreater(retry.kwargs['timeout'], first.kwargs['timeout'])

    def test_incomplete_http_body_is_retried(self):
        with patch.object(scraper, 'get_text', side_effect=[http.client.IncompleteRead(b'{"locations":['), '{"locations":[]}']) as request:
            self.assertEqual(scraper.load_clever_locations(), {'locations': []})
        self.assertEqual(request.call_count, 2)

    def test_failed_retry_retains_only_previously_successful_locations(self):
        previous = [{'brand': 'Clever', 'source': 'clever.dk', 'location_id': 'old', 'source_updated': '2026-10-17T00:00:00Z'}]
        for failure in ('{"locations":[', http.client.IncompleteRead(b'{"locations":[')):
            errors = []
            with self.subTest(failure=type(failure).__name__), patch.object(scraper, 'get_text', side_effect=[failure, failure]) as request:
                rows, status = scraper.fetch_public_ev_locations(scraper.CLEVER_LOCATIONS_URL, lambda data: data['locations'], 'clever.dk', previous, errors, payload_loader=scraper.load_clever_locations)
            self.assertEqual(request.call_count, 2)
            self.assertEqual(rows[0]['location_id'], 'old')
            self.assertTrue(rows[0]['stale'])
            self.assertEqual(status['status'], 'stale')
            self.assertIn('cache-free retry', errors[0]['error'])
            self.assertIn('JSON', errors[0]['error'])
            self.assertNotIn('stale', previous[0])
