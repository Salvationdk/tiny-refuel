import unittest
from scripts.vehicle_spec_html import extract_reviewed_html
from scripts.vehicle_spec_open_data import match_export, match_engines


class SourceTests(unittest.TestCase):
    def test_html_context_and_explicit_units_ignore_scripts(self):
        source = {'make': 'Test', 'model': 'One', 'url': 'https://example.invalid/one', 'allowed_host': 'example.invalid',
                  'parser': 'reviewed_html', 'mapping_reviewed': True, 'identity_marker': 'Test One',
                  'html_rules': [{'field': 'batteri_kwh', 'pattern': r'Battery capacity\s+(?P<value>\d+)\s*(?P<unit>kWh)'}]}
        page = '<h1>Test One</h1><table><tr><td>Battery capacity</td><td>60 kWh</td></tr></table><script>Battery capacity 999 kWh</script>'
        rows, warnings = extract_reviewed_html(page, source)
        self.assertFalse(warnings)
        self.assertEqual(rows[0]['specifications'], {'batteri_kwh': 60})
        self.assertIsNone(rows[0]['year'])
        self.assertTrue(rows[0]['review_required'])
        self.assertEqual(extract_reviewed_html(page + '<p>Battery capacity 70 kWh</p>', source)[0], [])
        self.assertEqual(extract_reviewed_html(page, {**source, 'mapping_reviewed': False})[0], [])
        self.assertEqual(extract_reviewed_html(page, {**source, 'year': 2020})[0], [])
        self.assertEqual(extract_reviewed_html(page, {**source, 'identity_marker': 'Test Two'})[0], [])
        self.assertEqual(extract_reviewed_html(page, {**source, 'allowed_host': 'other.invalid'})[0], [])

    def test_ev_export_keeps_net_gross_year_variant_and_weak_source_status(self):
        data = {'vehicles': [{'make': {'name': 'Test'}, 'model': {'name': 'One'}, 'year': 2020,
              'variant': {'name': 'Long range'}, 'battery': {'pack_capacity_kwh_net': 60, 'pack_capacity_kwh_gross': 65},
              'sources': [{'url': 'https://example.invalid'}]}]}
        missing = [{'make': 'TEST', 'model': 'One', 'missing': ['batteri_kwh']}]
        rows, report = match_export(data, missing, {'tag': 'v1'})
        self.assertEqual(report['matched_models'], 1)
        self.assertEqual(rows[0]['battery_capacities'], {'net_kwh': 60, 'gross_kwh': 65})
        self.assertEqual(rows[0]['year'], 2020)
        self.assertEqual(rows[0]['variant'], 'Long range')
        self.assertFalse(rows[0]['manufacturer_verified'])
        self.assertEqual(rows[0]['source_quality'], 'generic_or_missing_links')
        data['vehicles'][0]['battery']['pack_capacity_kwh_net'] = 70
        self.assertEqual(match_export(data, missing, {})[1]['rejected_ambiguous'][0]['reason'], 'net_capacity_exceeds_gross')

    def test_no_fuzzy_matches_without_reviewed_alias(self):
        data = {'vehicles': [{'make': {'name': 'Test'}, 'model': {'name': 'A4'}, 'battery': {'pack_capacity_kwh_net': 60}}]}
        missing = [{'make': 'Test', 'model': 'A 4', 'missing': ['batteri_kwh']}]
        self.assertEqual(match_export(data, missing, {})[0], [])
        alias = {'source_make': 'Test', 'source_model': 'A4', 'make': 'Test', 'model': 'A 4', 'reviewed': True}
        self.assertEqual(match_export(data, missing, {}, [alias])[0][0]['mapping'], 'reviewed_alias')
        with self.assertRaises(ValueError):match_export(data, missing, {}, [{**alias, 'reviewed': False}])
        self.assertEqual(match_export(data, missing * 2, {}, [alias])[0], [])

    def test_engine_litres_do_not_confuse_gallons_or_consumption_and_keep_generation(self):
        engine = {'label': '2.0', 'fuelType': 'Gasoline', 'specs': {'ENGINE SPECS / Fuel capacity': '13.2 gallons (50 L)', 'FUEL ECONOMY / Combined': '7 L/100km'}}
        data = [{'group': 'test', 'makes': [{'name': 'Test', 'models': [{'name': 'One', 'generations': [{'name': 'One II', 'yearStart': 2010, 'yearEnd': 2015, 'engines': [engine]}]}]}]}]
        missing = [{'make': 'Test', 'model': 'One', 'missing': ['tank_l', 'brændstof']}]
        rows, report = match_engines(data, missing, {'repository': 'example/data', 'commit': 'abc'})
        self.assertEqual(rows[0]['specifications'], {'tank_l': 50, 'brændstof': 'Benzin'})
        self.assertEqual(rows[0]['year_start'], 2010)
        self.assertEqual(rows[0]['generation'], 'One II')
        self.assertEqual(report['dataset_engine_rows'], 1)
        engine['specs']['ENGINE SPECS / Fuel capacity'] = '13.2 gallons'
        self.assertNotIn('tank_l', match_engines(data, missing, {'repository': 'x', 'commit': 'a'})[0][0]['specifications'])
