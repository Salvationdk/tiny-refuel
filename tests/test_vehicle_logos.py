import unittest
import json
from pathlib import Path
from scripts.prepare_vehicle_logos import sanitize_svg
from scripts.vehicle_catalog import load_catalog

class VehicleLogoTests(unittest.TestCase):
    def test_prepared_assets_are_self_contained_and_have_source(self):
        d=load_catalog(Path('custom_components/tiny_refuel/frontend/katalog.json'))
        self.assertEqual(len(d['logo_assets']), 212)
        for name,asset in d['logo_assets'].items():
            self.assertIn('<svg',sanitize_svg(d['logos'][name]))
            self.assertTrue(asset['source_url'].startswith('https://'))
            self.assertEqual(__import__('hashlib').sha256(d['logos'][name].encode()).hexdigest(), asset['sha256'])
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

    def test_local_static_mask_is_supported_but_remote_mask_is_rejected(self):
        svg='<svg viewBox="0 0 10 10"><defs><mask id="m" style="mask-type:luminance"><path fill="#fff" d="M0 0h10v10H0z"/></mask></defs><path mask="url(#m)" d="M0 0h10v10H0z"/></svg>'
        self.assertIn('mask="url(#m)"',sanitize_svg(svg))
        with self.assertRaises(ValueError):sanitize_svg(svg.replace('url(#m)','url(https://example.com/m)'))

    def test_traces_are_paths_and_original_packaged_rasters_are_retained(self):
        d=load_catalog(Path('custom_components/tiny_refuel/frontend/katalog.json'))
        traced=[n for n,a in d['logo_assets'].items() if a.get('origin')=='raster_trace']
        self.assertEqual(len(traced),16)
        for n in traced:
            self.assertNotIn('<image',d['logos'][n])
            self.assertIn('<path',d['logos'][n])
            self.assertTrue(d['logo_assets'][n]['visual_reviewed'])
            self.assertEqual(len(d['logo_assets'][n]['source_sha256']),64)
        for n in ['Leapmotor','NIO','Zeekr','Navor']:
            self.assertIn(n,d['logo_raster_sources'])
            self.assertNotIn(n,d['logo_pngs'])
        self.assertIn('Hongqi',d['logo_pngs'])
        self.assertFalse(d['logo_urls'])
