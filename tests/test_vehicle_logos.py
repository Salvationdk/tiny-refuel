import unittest
import json
from pathlib import Path
from scripts.prepare_vehicle_logos import sanitize_svg

class VehicleLogoTests(unittest.TestCase):
    def test_prepared_assets_are_self_contained_and_have_source(self):
        d=json.loads(Path('custom_components/tiny_refuel/frontend/bilkatalog.json').read_text(encoding='utf-8'))
        self.assertEqual(len(d['logo_assets']),148)
        for name,asset in d['logo_assets'].items():
            self.assertIn('<svg',sanitize_svg(d['logos'][name]))
            self.assertTrue(asset['source_url'].startswith(('https://github.com/simple-icons/','https://github.com/vehiclespecs/','https://github.com/detain/svg-logos/','https://github.com/tipstrade/node-vehicle-logos/','https://github.com/cardog-ai/icons/')))
            self.assertEqual(len(asset['sha256']),64)
    def test_active_and_external_content_is_rejected(self):
        for content in ('<script/>','<foreignObject/>','<image href="https://x"/>','<path onclick="x"/>','<path fill="url(https://x)"/>'):
            with self.assertRaises(ValueError):sanitize_svg('<svg viewBox="0 0 24 24">'+content+'</svg>')
        with self.assertRaises(ValueError):sanitize_svg('<!DOCTYPE svg><svg viewBox="0 0 24 24"/>')

    def test_static_gradients_and_inline_paint_are_preserved(self):
        svg = '<svg viewBox="0 0 24 24" preserveAspectRatio="xMidYMid meet"><defs><linearGradient id="paint"><stop offset="0" stop-color="#000"/></linearGradient></defs><path style="fill:url(#paint);stroke:#fff" d="M0 0L24 24"/></svg>'
        cleaned=sanitize_svg(svg)
        self.assertIn('fill="url(#paint)"', cleaned)
        self.assertIn('linearGradient',cleaned)
        self.assertNotIn('style=',cleaned)
        for paint in ('url(https://example.com/x)','url(data:image/svg+xml,x)','url(javascript:x)'):
            with self.assertRaises(ValueError):
                sanitize_svg('<svg viewBox="0 0 24 24"><path style="fill:'+paint+'"/></svg>')

    def test_coverage_report_accounts_for_every_register_make(self):
        report=json.loads(Path('scripts/data/vehicle-logo-coverage.json').read_text(encoding='utf-8'))
        self.assertEqual(len(report['makes']), report['summary']['register_makes'])
        self.assertEqual(report['summary']['covered']+report['summary']['pending'],len(report['makes']))
        for row in report['makes']:
            if row['status']=='pending':self.assertIn('reason',row)
