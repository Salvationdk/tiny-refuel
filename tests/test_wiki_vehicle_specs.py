import unittest
from scripts.wiki_vehicle_specs import capacity, extract


class WikiSpecsTests(unittest.TestCase):
    def test_explicit_units_and_reserve_but_no_ranges_or_ambiguous_gallons(self):
        self.assertEqual(capacity('{{convert|9.2|L|abbr=on}} (Reserve: {{convert|2|L}})'), 9.2)
        self.assertAlmostEqual(capacity('{{convert|2|usgal|L}}'), 7.570824)
        self.assertEqual(capacity('540 kWh', True), 540)
        for value in ['14–17 L', '{{convert|14|to|17|L}}', '3,000 L', '14 L / 17 L', '12 gal', '12 V 10 Ah']:
            self.assertIsNone(capacity(value))

    def test_exact_identity_and_revision_provenance(self):
        text = '{{Infobox motorcycle|name=CG125|manufacturer=[[Honda]]|fuel_capacity={{convert|9.2|L|abbr=on}}<ref>source</ref>|engine=124 cc}}'
        page = {'revisions': [{'revid': 123, 'slots': {'main': {'*': text}}}]}
        rows, status = extract(page, 'Honda', 'CG125')
        self.assertEqual(status, 'candidates')
        self.assertEqual(rows[0]['specifications'], {'tank_l': 9.2})
        self.assertFalse(rows[0]['reviewed'])
        self.assertTrue(rows[0]['source_url'].endswith('oldid=123'))
        self.assertEqual(extract(page, 'Honda', 'CG150')[0], [])
        self.assertEqual(extract(page, 'Other', 'CG125')[0], [])
