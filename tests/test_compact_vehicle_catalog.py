from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from scripts.compact_vehicle_catalog import compact_stream, compact_file


class CompactCatalogTests(unittest.TestCase):
    def test_only_model_profiles_removed_with_chunked_escaped_strings_and_unicode(self):
        model = {'model': 'Æ \\" [ ]', 'variants': [{'name': 'Diesel', 'fuel_types': ['Diesel']}],
                 'dmr_profiles': [{'a': 'x' * 70000 + '"end\\', 'values': [1, 0.03, True, None]}],
                 'model_years': ['2020'], 'tank_l': 50}
        catalog = {'brands': [{'mærke': 'Citroën', 'modeller': [model, {'model': 'B', 'dmr_profiles': []}]}],
                   'logos': {'Citroën': '<svg>' + ('A' * 70000) + '</svg>'},
                   'custom': {'dmr_profiles': [1, 2]}}
        output = StringIO()
        stats = compact_stream(StringIO(json.dumps(catalog, ensure_ascii=False)), output)
        result = json.loads(output.getvalue())
        del model['dmr_profiles']
        del catalog['brands'][0]['modeller'][1]['dmr_profiles']
        self.assertEqual(result, catalog)
        self.assertEqual(stats, {'models': 2, 'profile_fields_removed': 2, 'technical_profiles_removed': 1})

    def test_invalid_or_truncated_input_does_not_replace_output_or_original(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'source.json', Path(folder) / 'result.json'
            output.write_text('keep previous')
            for invalid in ('{"brands":[', '{"brands":[]}garbage',
                            '{"brands":[{"modeller":[{"dmr_profiles":[NaN]}]}]}',
                            '{"brands":[{"modeller":[{"dmr_profiles":[1,]}]}]}'):
                source.write_text(invalid)
                with self.assertRaises(ValueError):
                    compact_file(source, output)
                self.assertEqual(output.read_text(), 'keep previous')
                self.assertEqual(source.read_text(), invalid)
            with self.assertRaises(ValueError):
                compact_file(source, source)
            self.assertEqual(len(list(Path(folder).iterdir())), 2)

    def test_atomic_file_output_and_original_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'source.json', Path(folder) / 'result.json'
            original = '{"brands":[{"modeller":[{"model":"A","dmr_profiles":[{}]}]}]}'
            source.write_text(original)
            stats = compact_file(source, output)
            self.assertEqual(source.read_text(), original)
            self.assertTrue(stats['original_preserved'])
            self.assertLess(stats['output_bytes'], stats['input_bytes'])
            self.assertNotIn('dmr_profiles', output.read_text())
