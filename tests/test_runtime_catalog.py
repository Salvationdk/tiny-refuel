import json
from pathlib import Path
import unittest
from scripts.validate_vehicle_catalog import validate_catalog

ROOT = Path(__file__).parents[1]


class RuntimeCatalogTests(unittest.TestCase):
    def test_one_embedded_catalog_with_no_runtime_parts_or_variants(self):
        folder = ROOT / 'custom_components/tiny_refuel/frontend'
        data = json.loads((folder / 'katalog.json').read_text())
        self.assertEqual(validate_catalog(data), {'makes': 89, 'models': 895, 'models_with_capacity': 895})
        self.assertFalse((folder / 'bilkatalog.json').exists())
        self.assertNotIn('catalog_parts', data)
        self.assertTrue(all('variants' not in model for brand in data['brands'] for model in brand['modeller']))
        self.assertEqual(len(data['logos']), 261)
        self.assertEqual(len(data['logo_pngs']), 20)
        for source in data['data_sources'].values():
            self.assertTrue(source.get('license_text'))

    def test_custom_catalog_and_invalid_fields(self):
        valid = {'brands': [{'mærke': 'Eget mærke', 'modeller': [{'model': 'Min model', 'brændstof': 'el', 'batteri_kwh': 4.5}]}]}
        self.assertEqual(validate_catalog(valid)['models'], 1)
        for bad in (True, -1, 0, '35', float('inf')):
            row = {'brands': [{'mærke': 'Test', 'modeller': [{'model': 'X', 'tank_l': bad}]}]}
            with self.assertRaises(ValueError):validate_catalog(row)
        with self.assertRaises(ValueError):validate_catalog({'brands': [{'mærke': 'Test', 'modeller': [{'model': 'X'}, {'model': 'x'}]}]})
        with self.assertRaises(ValueError):validate_catalog({'catalog_parts': ['x'], 'brands': []})
