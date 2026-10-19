"""National tariffs keep their own provenance on failure and recover cleanly."""
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('tariff_scraper',Path(__file__).parents[1]/'custom_components/tiny_refuel/scraper.py')
scraper=importlib.util.module_from_spec(spec);spec.loader.exec_module(scraper)

class TariffTests(unittest.TestCase):
    def test_failures_retain_only_same_provider_tariffs(self):
        old=[{'brand':'Q8','name':'Normal','kwh':3,'address':'','source_updated':'old'},
             {'brand':'Q8','address':'Road 1','kwh':4}, {'brand':'OK','name':'Normal','kwh':2}]
        result=scraper.merge_tariff_cache([],old,[{'q8_el':'offline'}],'new','fallback')
        self.assertEqual(len(result),1);self.assertTrue(result[0]['stale'])
        self.assertEqual(result[0]['source_updated'],'old');self.assertNotIn('stale',old[0])
    def test_success_replaces_stale_tariff_and_stamps_fetch(self):
        fresh=[{'brand':'Q8','name':'Normal','kwh':3.5}]
        result=scraper.merge_tariff_cache(fresh,[{'brand':'Q8','name':'Normal','kwh':3,'stale':True}],[],'new')
        self.assertEqual(len(result),1);self.assertFalse(result[0].get('stale'))
        self.assertEqual(result[0]['source_updated'],'new')
