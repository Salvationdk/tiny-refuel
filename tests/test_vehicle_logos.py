import unittest
import json
from pathlib import Path
from scripts.prepare_vehicle_logos import sanitize_svg

class VehicleLogoTests(unittest.TestCase):
    def test_prepared_assets_are_self_contained_and_have_source(self):
        d=json.loads(Path('custom_components/tiny_refuel/frontend/bilkatalog.json').read_text(encoding='utf-8'))
        self.assertEqual(len(d['logo_assets']),38)
        for name,asset in d['logo_assets'].items():
            self.assertIn('<svg',sanitize_svg(d['logos'][name]))
            self.assertTrue(asset['source_url'].startswith(('https://github.com/simple-icons/','https://github.com/vehiclespecs/')))
            self.assertEqual(len(asset['sha256']),64)
    def test_active_and_external_content_is_rejected(self):
        for content in ('<script/>','<foreignObject/>','<image href="https://x"/>','<path onclick="x"/>','<path fill="url(https://x)"/>'):
            with self.assertRaises(ValueError):sanitize_svg('<svg viewBox="0 0 24 24">'+content+'</svg>')
        with self.assertRaises(ValueError):sanitize_svg('<!DOCTYPE svg><svg viewBox="0 0 24 24"/>')
