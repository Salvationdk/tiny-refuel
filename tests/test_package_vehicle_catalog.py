"""The distributed catalog must reconstruct exactly and reject incomplete input."""
import json
from pathlib import Path
import tempfile
import unittest
from scripts.package_vehicle_catalog import package
from scripts.vehicle_catalog import load_catalog


class PackagedCatalogTests(unittest.TestCase):
    def test_roundtrip_across_unicode_boundaries_and_missing_part(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = root / 'source.json', root / 'bilkatalog.json'
            expected = {'brands': [{'mærke': 'ÆØÅ🚗', 'modeller': []}], 'padding': 'æ🚗' * 400000}
            source.write_text(json.dumps(expected, ensure_ascii=False), encoding='utf-8')
            package(source, target)
            self.assertEqual(load_catalog(target), expected)
            manifest = json.loads(target.read_text())
            self.assertGreater(len(manifest['catalog_parts']), 1)
            (root / manifest['catalog_parts'][0]).unlink()
            with self.assertRaises(FileNotFoundError):
                load_catalog(target)

    def test_plain_catalog_and_invalid_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'catalog.json'
            path.write_text('{"brands": []}')
            self.assertEqual(load_catalog(path), {'brands': []})
            for parts in ([], ['../outside.txt'], ['https://example.com/file.txt'], 'invalid'):
                path.write_text(json.dumps({'catalog_parts': parts}))
                with self.assertRaises(ValueError):
                    load_catalog(path)

    def test_model_index_defers_details_and_full_read_preserves_every_field(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = root / 'source.json', root / 'bilkatalog.json'
            expected = {'brands': [{'mærke': 'Test', 'modeller': [
                {'model': 'A', 'requires_fuel_selection': True, 'brændstof': None, 'tank_l': None,
                 'source_url': 'https://example.com', 'specification_note': 'Manual check',
                 'model_years': [2020], 'variants': [{'name': 'Electric', 'fuel_types': ['El']}]},
                {'model': 'B', 'brændstof': 'benzin', 'tank_l': 35, 'custom': {'preserve': True}},
            ]}], 'logos': {'Test': '<svg/>'}}
            source.write_text(json.dumps(expected))
            package(source, target)
            self.assertEqual(load_catalog(target), expected)
            index = load_catalog(target, details=False)
            self.assertNotIn('variants', index['brands'][0]['modeller'][0])
            self.assertNotIn('model_years', index['brands'][0]['modeller'][0])
            self.assertEqual(index['brands'][0]['modeller'][1]['tank_l'], 35)
            detail = next((root / 'catalog-details').glob('*.json'))
            detail.unlink()
            self.assertEqual(load_catalog(target, details=False), index)
            with self.assertRaises(FileNotFoundError): load_catalog(target)
