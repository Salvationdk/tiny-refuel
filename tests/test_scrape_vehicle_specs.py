import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

SPEC = importlib.util.spec_from_file_location('spec_scraper', Path(__file__).parents[1] / 'scripts/scrape_vehicle_specs.py')
scraper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scraper)


def page(**overrides):
    vehicle = {'@type': 'Car', 'brand': {'name': 'Example'}, 'model': 'One',
               'vehicleModelDate': '2020', 'vehicleConfiguration': 'Long range',
               'fuelType': 'Electricity', 'fuelCapacity': {'value': 60, 'unitCode': 'KWH'}}
    vehicle.update(overrides)
    return '<script type="application/ld+json">' + json.dumps({'@graph': [vehicle]}) + '</script>'


SOURCE = {'make': 'Example', 'model': 'One', 'url': 'https://example.invalid/one', 'year': 2020, 'variant': 'Long range'}


class ScraperTests(unittest.TestCase):
    def test_inventory_applicability_and_excluded_type(self):
        data = {'brands': [{'mærke': 'Example', 'modeller': [
            {'model': 'Petrol', 'fuel_types': ['Benzin']},
            {'model': 'Electric', 'fuel_types': ['El']},
            {'model': 'Hybrid', 'fuel_types': ['Plug-in hybrid'], 'tank_l': 40},
            {'model': 'Unknown'},
            {'model': 'Complete', 'brændstof': 'Diesel', 'tank_l': 50},
            {'model': 'Tool', 'vehicle_types': ['Motorredskab']},
        ]}]}
        rows = {r['model']: r for r in scraper.inventory(data)}
        self.assertEqual(rows['Petrol']['missing'], ['tank_l'])
        self.assertEqual(rows['Electric']['missing'], ['batteri_kwh'])
        self.assertEqual(rows['Hybrid']['missing'], ['batteri_kwh'])
        self.assertEqual(rows['Unknown']['missing'], ['brændstof', 'tank_l', 'batteri_kwh'])
        self.assertNotIn('Complete', rows)
        self.assertNotIn('Tool', rows)

    def test_exact_vehicle_year_variant_and_explicit_units(self):
        result, warnings = scraper.extract(page(), SOURCE)
        self.assertFalse(warnings)
        self.assertEqual(result[0]['specifications'], {'brændstof': 'El', 'batteri_kwh': 60})
        for override in ({'model': 'Other'}, {'brand': 'Other'}, {'vehicleModelDate': '2021'},
                         {'vehicleConfiguration': 'Standard'}, {'@type': 'Product'}, {'model': None}):
            self.assertEqual(scraper.extract(page(**override), SOURCE)[0], [])
        result, _ = scraper.extract(page(fuelCapacity={'value': 180, 'unitCode': 'AMH'}), SOURCE)
        self.assertNotIn('batteri_kwh', result[0]['specifications'])

    def test_capacity_conversion_and_invalid_values(self):
        self.assertEqual(scraper.quantity({'value': '42,5', 'unitText': 'litres'}, 'tank_l'), 42.5)
        self.assertEqual(scraper.quantity({'value': 60000, 'unitText': 'Wh'}, 'batteri_kwh'), 60)
        self.assertAlmostEqual(scraper.quantity({'value': 10, 'unitCode': 'GLL'}, 'tank_l'), 37.854118)
        for value in (True, -5, 0, 'NaN', 'Infinity', None):
            self.assertIsNone(scraper.quantity({'value': value, 'unitText': 'kWh'}, 'batteri_kwh'))
        self.assertIsNone(scraper.quantity(60, 'batteri_kwh'))
        self.assertIsNone(scraper.quantity({'value': 60}, 'batteri_kwh'))

    def test_conflicting_battery_sizes_are_not_silently_selected(self):
        result, warnings = scraper.extract(page(additionalProperty=[
            {'name': 'Usable battery capacity', 'value': 55, 'unitText': 'kWh'},
            {'name': 'Gross battery capacity', 'value': 60, 'unitText': 'kWh'},
        ]), SOURCE)
        self.assertEqual(result, [])
        self.assertIn('conflicting_capacity_in_vehicle_node', warnings)

    def test_invalid_structured_data_and_duplicates(self):
        result, warnings = scraper.extract('<script type="application/ld+json">{bad}</script>' + page() * 2, SOURCE)
        self.assertEqual(len(result), 1)
        self.assertEqual(warnings, ['invalid_json_ld'])

    def test_offline_end_to_end_and_input_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / 'catalog.json'
            original = json.dumps({'brands': [{'mærke': 'Example', 'modeller': [{'model': 'One', 'fuel_types': ['El']}, {'model': 'Two'}]}]})
            catalog.write_text(original)
            sources = root / 'sources.json'
            sources.write_text(json.dumps([SOURCE, {**SOURCE, 'url': 'https://example.invalid/error'}]))
            args = SimpleNamespace(catalog=str(catalog), output=str(root / 'results'), sources=str(sources), delay=1)
            with patch.object(scraper.Fetcher, 'get', side_effect=[page(), ValueError('blocked')]):
                scraper.run(args)
            self.assertEqual(catalog.read_text(), original)
            candidates = json.loads((root / 'results/candidates.json').read_text())
            self.assertEqual(candidates[0]['missing_fields_found'], ['batteri_kwh'])
            self.assertTrue(candidates[0]['review_required'])
            self.assertEqual(len(candidates[0]['page_sha256']), 64)
            self.assertEqual(json.loads((root / 'results/without-source.json').read_text())[0]['model'], 'Two')
            self.assertEqual(json.loads((root / 'results/source-status.json').read_text())[1]['status'], 'error')


if __name__ == '__main__':
    unittest.main()
