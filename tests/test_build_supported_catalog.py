import unittest
from copy import deepcopy
from scripts.build_supported_catalog import supported_catalog


class SupportedCatalogTests(unittest.TestCase):
    def test_capacity_filter_and_motor_tools_without_mutating_input(self):
        models = [
            {'model': 'Tank', 'tank_l': 45, 'vehicle_types': ['Personbil']},
            {'model': 'Battery', 'batteri_kwh': 60},
            {'model': 'Hybrid', 'tank_l': 40, 'batteri_kwh': 10},
            {'model': 'No data'}, {'model': 'Negative', 'tank_l': -40},
            {'model': 'Boolean', 'tank_l': True}, {'model': 'Infinite', 'batteri_kwh': float('inf')},
            {'model': 'Tool', 'tank_l': 80, 'vehicle_types': ['Motorredskab']},
            {'model': 'Tool code', 'tank_l': 80, 'vehicle_type': '12'},
        ]
        source = {'brands': [{'mærke': 'Test', 'modeller': models}, {'mærke': 'Empty', 'modeller': [{'model': 'Nothing'}]}], 'logos': {'Test': 'svg'}}
        original = deepcopy(source)
        result = supported_catalog(source)
        self.assertEqual(source, original)
        self.assertEqual([m['model'] for m in result['brands'][0]['modeller']], ['Tank', 'Battery', 'Hybrid'])
        self.assertEqual(result['brands'][0]['modeller'][0]['vehicle_types'], ['Personbil'])
        self.assertEqual(len(result['brands']), 1)
        self.assertEqual(result['capacity_filter']['excluded_motor_tools'], 2)
        self.assertEqual(result['logos'], original['logos'])
