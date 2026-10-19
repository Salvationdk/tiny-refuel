import unittest
from scripts.build_enriched_vehicle_catalog import enrich_catalog


class EnrichedCatalogTests(unittest.TestCase):
    def test_existing_capacity_is_preserved_and_variant_inventory_is_omitted(self):
        original = {'brands': [{'mærke': 'Test', 'modeller': [{'model': 'One', 'tank_l': 45, 'variants': [{'name': 'Old'}]}]}]}
        rows = [{'make': 'Test', 'model': 'One', 'variant': 'New', 'specifications': {'tank_l': 50}}]
        result = enrich_catalog(original, rows)
        model = result['brands'][0]['modeller'][0]
        self.assertEqual(model['tank_l'], 45)
        self.assertNotIn('variants', model)
        self.assertIn('variants', original['brands'][0]['modeller'][0])

    def test_only_unique_capacity_values_fill_empty_models(self):
        original = {'brands': [{'mærke': 'Test', 'modeller': [{'model': 'One', 'fuel_types': ['Benzin']}, {'model': 'Two'}]}]}
        rows = [{'make': 'Test', 'model': 'One', 'specifications': {'tank_l': 50}},
                {'make': 'Test', 'model': 'Two', 'variant': 'A', 'specifications': {'tank_l': 40}},
                {'make': 'Test', 'model': 'Two', 'variant': 'B', 'specifications': {'tank_l': 60}}]
        result = enrich_catalog(original, rows)
        self.assertEqual(len(result['brands'][0]['modeller']), 1)
        self.assertEqual(result['brands'][0]['modeller'][0]['brændstof'], 'benzin')
        self.assertEqual(result['brands'][0]['modeller'][0]['tank_l'], 50)
        self.assertIn('not_manufacturer_verified', result['brands'][0]['modeller'][0]['capacity_status'])

    def test_ambiguous_usable_battery_must_not_fall_back_to_single_gross_value(self):
        original = {'brands': [{'mærke': 'Test', 'modeller': [{'model': 'One'}]}]}
        rows = [{'make': 'Test', 'model': 'One', 'variant': str(n), 'battery_basis': 'usable',
                 'specifications': {'batteri_kwh': n}, 'battery_capacities': {'net_kwh': n, 'gross_kwh': 70}} for n in (50, 60)]
        self.assertEqual(enrich_catalog(original, rows)['brands'], [])
