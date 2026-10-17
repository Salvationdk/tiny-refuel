"""Public GET recovery must be bounded and never retry permanent HTTP errors."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location('http_scraper', Path(__file__).parents[1] / 'custom_components/tiny_refuel/scraper.py')
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)


class HttpTests(unittest.TestCase):
    def test_transient_http_error_is_retried_once(self):
        for status in (500, 502, 503, 504):
            with self.subTest(status=status):
                response = MagicMock()
                response.__enter__.return_value.read.return_value = b'ok'
                with patch.object(scraper.urllib.request, 'urlopen', side_effect=[HTTPError('https://example.test', status, 'error', {}, None), response]) as get, patch.object(scraper.time, 'sleep'):
                    self.assertEqual(scraper.get('https://example.test'), b'ok')
                self.assertEqual(get.call_count, 2)

    def test_retry_is_bounded_and_permanent_errors_are_not_retried(self):
        for status, attempts in ((500, 2), (403, 1), (404, 1), (429, 1)):
            with self.subTest(status=status):
                with patch.object(scraper.urllib.request, 'urlopen', side_effect=HTTPError('https://example.test', status, 'error', {}, None)) as get, patch.object(scraper.time, 'sleep'):
                    with self.assertRaises(HTTPError):
                        scraper.get('https://example.test')
                self.assertEqual(get.call_count, attempts)
