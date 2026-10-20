import unittest
from scripts.catalog_inventory import inventory


class CatalogInventoryTests(unittest.TestCase):
    def test_unique_models_overlapping_categories_and_missing_capacity(self):
        result = inventory({'brands': [{'mærke': 'Test', 'modeller': [
            {'model': 'Mixed', 'vehicle_types': ['personbil', 'varebil'], 'tank_l': 50, 'brændstof': 'benzin'},
            {'model': 'mixed', 'vehicle_types': ['varebil']},
            {'model': 'Electric', 'vehicle_types': ['lastbil'], 'brændstof': 'el', 'batteri_kwh': 460},
            {'model': 'Tractor', 'vehicle_type': '8', 'brændstof': 'diesel'},
            {'model': 'Unknown', 'tank_l': 40},
        ]}]})
        self.assertEqual(result['summary']['unique_models'], 4)
        self.assertEqual(result['summary']['by_type']['varebil'], 1)
        self.assertEqual(result['summary']['by_type']['lastbil'], 1)
        self.assertEqual(result['summary']['by_type']['traktor'], 1)
        self.assertEqual(result['summary']['unclassified_models'], 1)
        self.assertEqual(result['summary']['models_with_capacity'], 3)
        self.assertEqual(next(r for r in result['missing'] if r['model'] == 'Tractor')['missing_fields'], ['tank_l'])
        self.assertEqual(next(r for r in result['missing'] if r['model'] == 'Unknown')['missing_fields'], ['brændstof'])
