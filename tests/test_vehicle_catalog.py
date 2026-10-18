"""Model imports must preserve specifications and require reviewed candidates."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('vehicle_catalog', ROOT / 'scripts/vehicle_catalog.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VehicleCatalogTests(unittest.TestCase):
    def test_toyota_reads_both_live_list_shape_and_dictionary_shape(self):
        rows = [
            [{'model': {'name': 'Toyota Proace Max', 'subModels': [{'name': 'Proace Max Electric'}]}}],
            {'PM': {'name': 'Toyota Proace Max', 'subModels': [{'name': 'Proace Max Electric'}]}},
        ]
        for mapping in rows:
            with self.subTest(mapping=mapping):
                result = module.toyota_candidates('<script>' + json.dumps({'modelMap': mapping}) + '</script>')
                self.assertFalse(result['reviewed'])
                self.assertEqual(result['brands'][0]['models'], ['Proace Max', 'Proace Max Electric'])
                self.assertNotIn('brændstof', result['brands'][0])

    def test_changed_source_is_rejected_instead_of_returning_an_empty_catalog(self):
        for page in ('<p>Review: I love my Toyota</p>', '{"modelMap": {}}', '{"modelMap": broken}'):
            with self.assertRaises(ValueError):
                module.toyota_candidates(page)

    def test_merge_requires_review_and_preserves_existing_specs_logos_and_unknown_metadata(self):
        original = {'brands': [{'mærke': 'Toyota', 'modeller': [{'model': 'Aygo', 'brændstof': 'benzin', 'tank_l': 35}]}], 'logos': {'Toyota': 'SVG'}, 'custom': True}
        candidates = {'reviewed': False, 'brands': [{'mærke': 'Toyota', 'source_url': 'https://www.toyota.dk', 'models': ['AYGO', 'Proace Max', 'Proace Max']}]}
        with self.assertRaises(ValueError):
            module.merge_reviewed(original, candidates)
        candidates['reviewed'] = True
        merged, added = module.merge_reviewed(original, candidates)
        self.assertEqual(added, ['Toyota Proace Max'])
        self.assertEqual(merged['logos'], original['logos'])
        self.assertTrue(merged['custom'])
        self.assertEqual(merged['brands'][0]['modeller'][0], original['brands'][0]['modeller'][0])
        new = merged['brands'][0]['modeller'][1]
        self.assertIsNone(new['brændstof'])
        self.assertIsNone(new['tank_l'])
        self.assertNotIn('batteri_kwh', new)
        self.assertTrue(new['requires_fuel_selection'])
        self.assertEqual(len(original['brands'][0]['modeller']), 1)
        again, repeated = module.merge_reviewed(merged, candidates)
        self.assertEqual(again, merged)
        self.assertEqual(repeated, [])

    def test_checked_additions_are_present_without_duplicate_names_or_invented_specs(self):
        catalog = module.load_catalog(ROOT / 'custom_components/tiny_refuel/frontend/bilkatalog.json')
        self.assertEqual(len(catalog['brands']), 54)
        self.assertEqual(sum(len(row['modeller']) for row in catalog['brands']), 470)
        new = []
        for brand in catalog['brands']:
            names = [row['model'].casefold() for row in brand['modeller']]
            self.assertEqual(len(names), len(set(names)))
            new.extend(row for row in brand['modeller'] if row.get('requires_fuel_selection'))
        self.assertTrue(all(any(isinstance(row.get(k), (int, float)) and row[k] > 0 for k in ('tank_l', 'batteri_kwh')) for brand in catalog['brands'] for row in brand['modeller']))
        self.assertTrue(all(row['source_url'].startswith('https://') for row in new))
        for row in new:
            for field in ('brændstof', 'tank_l', 'batteri_kwh'):
                if row.get(field) is not None:
                    self.assertEqual(row[field], row['preserved_specification'][field])
