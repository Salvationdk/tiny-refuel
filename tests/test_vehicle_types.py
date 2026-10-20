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
                self.assertTrue(set(types) <= {'personbil', 'varebil', 'andet', 'lastbil', 'bus', 'motorcykel', 'knallert', 'traktor'})

    def test_manufacturer_additions_are_scoped_idempotent_and_retain_provenance(self):
        from collections import Counter
        from scripts.add_reviewed_vehicle_models import ADDITIONS, add_reviewed_models
        additions = json.loads(ADDITIONS.read_text())['models']
        self.assertEqual(Counter(r['vehicle_types'][0] for r in additions),
                         dict.fromkeys(['lastbil', 'bus', 'motorcykel', 'knallert', 'traktor', 'andet'], 3))
        original = {'brands': [{'mærke': 'Honda', 'modeller': [{'model': 'CB500 Hornet', 'tank_l': 18}]}]}
        result = add_reviewed_models(original)
        self.assertEqual(add_reviewed_models(result), result)
        self.assertEqual(original['brands'][0]['modeller'][0]['tank_l'], 18)
        self.assertEqual(next(b for b in result['brands'] if b['mærke'] == 'Honda')['modeller'][0]['tank_l'], 18)
        rebuilt = enrich_catalog(add_reviewed_models({'brands': []}), [])
        models = [m for b in rebuilt['brands'] for m in b['modeller']]
        self.assertEqual(len(models), 18)
        for model in models:
            self.assertTrue(model['capacity_scope'])
            self.assertEqual(model['capacity_checked_at'], '2026-10-19')
            self.assertTrue(model['source_url'].startswith('https://'))
            self.assertEqual(model['capacity_source_urls'], [model['source_url']])
            self.assertIn('Kontrollér', model['specification_note'])
        self.assertEqual(next(m for m in models if m['model'] == 'CB500 Hornet')['model_years'], [2024])
