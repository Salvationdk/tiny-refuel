"""Tesla public pricing: country, access, fees, time schedules and failed fetches."""
import importlib.util
import json
from pathlib import Path
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('tesla_scraper', Path(__file__).parents[1] / 'custom_components/tiny_refuel/scraper.py')
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)


def book(price, member=True, **extra):
    return dict(feeType='CHARGING', currencyCode='DKK', uom='kwh', rateBase=price,
                vehicleMakeType='TSLA' if member else 'NTSLA', isMemberPricebook=member, **extra)


def page(books, country='DK', others=True, site='27396'):
    props = {'locationSlug': site, 'formattedData': {'chargerDetails': {
        'address': {'countryCode': country}, 'openToPublic': True,
        'openToNonTeslas': others, 'maxPowerKw': 250, 'publicStallCount': 24,
        'effectivePricebooks': books}}}
    return '<script id="__NEXT_DATA__">' + json.dumps({'props': {'pageProps': props}}) + '</script>'


class TeslaTests(unittest.TestCase):
    def test_separate_prices_exclude_minute_fees_msp_and_other_currencies(self):
        fee = book(3); fee.update(feeType='CONGESTION', uom='min')
        msp = book(2.9, False); msp['vehicleMakeType'] = 'MSP'
        euro = book(.4); euro['currencyCode'] = 'EUR'
        result = scraper.normalize_tesla_detail(page([book(2.6), book(3.6, False), fee, msp, euro, book(2.6)]), '27396')
        self.assertEqual(result['tesla_prices']['member'], [{'price': 2.6, 'start': '', 'end': '', 'days': '', 'time_of_use': False}])
        self.assertEqual(result['tesla_prices']['non_member'][0]['price'], 3.6)
        self.assertIsNone(result['kwh'])
        self.assertFalse(result['app_only'])
        self.assertEqual(result['plugs'], 24)

    def test_preserves_time_windows_without_claiming_lowest_price_is_current(self):
        result = scraper.normalize_tesla_detail(page([
            book(2.6, isTou=True, startTime='00:00', endTime='16:00', days='Monday'),
            book(3.6, isTou=True, startTime='16:00', endTime='20:00', days='Monday')]), '27396')
        self.assertEqual(len(result['tesla_prices']['member']), 2)
        self.assertEqual(result['tesla_prices']['member'][1]['start'], '16:00')
        self.assertIsNone(result['kwh'])

    def test_legacy_site_slug_is_accepted(self):
        result = scraper.normalize_tesla_detail(page([book(2.6)], site='hjorringsupercharger'), 'hjorringsupercharger')
        self.assertFalse(result['app_only'])

    def test_country_site_and_non_tesla_access(self):
        for kwargs in [{'country': 'SE'}, {'site': 'wrong'}]:
            with self.assertRaises(ValueError):
                scraper.normalize_tesla_detail(page([book(2.6)], **kwargs), '27396')
        result = scraper.normalize_tesla_detail(page([book(2.6), book(3.6, False)], others=False), '27396')
        self.assertEqual(result['tesla_prices']['non_member'], [])

    def test_missing_or_unsupported_prices_stay_unknown(self):
        result = scraper.normalize_tesla_detail(page([book(2.6, rateTier1=5), book(-1), book('NaN')]), '27396')
        self.assertTrue(result['app_only'])
        self.assertEqual(result['tesla_prices'], {'member': [], 'non_member': []})

    def test_detail_failure_keeps_location_and_only_its_own_previous_prices(self):
        row = {'source': 'tesla.com', 'location_id': 'a', 'tesla_site_slug': '27396', 'address': 'Testvej', 'kwh': None}
        old = dict(row, tesla_prices={'member': [{'price': 2.6}], 'non_member': []}, tesla_price_updated='2026-10-08T00:00:00Z')
        status = {'status': 'ok'}; errors = []
        with patch.object(scraper, 'get_text', side_effect=HTTPError('test', 403, 'Forbidden', {}, None)):
            scraper.enrich_tesla_prices([row], status, [old], errors)
        self.assertEqual(row['address'], 'Testvej')
        self.assertTrue(row['tesla_price_stale'])
        self.assertEqual(row['tesla_price_updated'], old['tesla_price_updated'])
        self.assertEqual(status['price_errors'], 1)
        self.assertEqual(errors[0]['source'], 'tesla-prices')
        self.assertIn('HTTP 403 Forbidden', errors[0]['error'])

    def test_loader_uses_legacy_slug_instead_of_numeric_identifier(self):
        row = {'source': 'tesla.com', 'location_id': 'old', 'tesla_site_slug': 'hjorringsupercharger'}
        with patch.object(scraper, 'get_text', return_value=page([book(2.6)], site='hjorringsupercharger')) as get:
            errors = []
            scraper.enrich_tesla_prices([row], {'status': 'ok'}, [], errors)
        self.assertEqual(get.call_args.args[0],
                         'https://www.tesla.com/findus/location/supercharger/hjorringsupercharger')
        self.assertEqual(errors, [])
        self.assertEqual(row['tesla_prices']['member'][0]['price'], 2.6)

    def test_access_denied_stops_after_current_batch(self):
        rows = [{'source': 'tesla.com', 'location_id': str(i), 'tesla_site_slug': str(i)} for i in range(10)]
        with patch.object(scraper, 'get_text', side_effect=HTTPError('test', 403, 'Forbidden', {}, None)) as get:
            scraper.enrich_tesla_prices(rows, {'status': 'ok'}, [], [])
        self.assertEqual(get.call_count, 3)

    def test_list_failure_does_not_attempt_price_requests(self):
        with patch.object(scraper, 'get_text') as get:
            scraper.enrich_tesla_prices([{'source': 'tesla.com'}], {'status': 'stale'}, [], [])
        get.assert_not_called()

if __name__ == '__main__':
    unittest.main()
