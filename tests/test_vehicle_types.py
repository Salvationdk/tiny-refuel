import json
from pathlib import Path
import unittest
from scripts.apply_vehicle_types import apply_vehicle_types
from scripts.build_enriched_vehicle_catalog import enrich_catalog


class VehicleTypesTests(unittest.TestCase):
    def test_reviewed_types_and_unknown_models(self):
        source = {'brands': [{'mærke': 'Volkswagen', 'modeller': [
            {'model': 'up!', 'tank_l': 35}, {'model': 'Caddy Cargo', 'tank_l': 50},
            {'model': 'New model', 'tank_l': 40}, {'model': 'Golf', 'vehicle_types': ['custom']}]}]}
        models = apply_vehicle_types(source)['brands'][0]['modeller']
        self.assertEqual(models[0]['vehicle_types'], ['personbil'])
        self.assertEqual(models[1]['vehicle_types'], ['varebil'])
        self.assertNotIn('vehicle_types', models[2])
        self.assertEqual(models[3]['vehicle_types'], ['custom'])
        self.assertNotIn('vehicle_types', source['brands'][0]['modeller'][0])
        self.assertEqual(enrich_catalog(source, [])['brands'][0]['modeller'][0]['vehicle_types'], ['personbil'])

    def test_packaged_catalog_matches_review(self):
        source = json.loads(Path('custom_components/tiny_refuel/frontend/katalog.json').read_text())
        for brand in source['brands']:
            for model in brand['modeller']:
                types = model.pop('vehicle_types')
                rebuilt = apply_vehicle_types({'brands': [{'mærke': brand['mærke'], 'modeller': [model]}]})
                self.assertEqual(rebuilt['brands'][0]['modeller'][0]['vehicle_types'], types)
                self.assertTrue(set(types) <= {'personbil', 'varebil', 'andet'})
