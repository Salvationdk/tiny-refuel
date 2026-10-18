import unittest
from scripts.review_vehicle_specs import review


def candidate(value=50, **kwargs):
    return {'make': 'Example', 'model': 'One', 'year': 2020, 'variant': 'Standard',
            'specifications': {'tank_l': value}, **kwargs}


class ReviewTests(unittest.TestCase):
    def test_same_scope_conflicts_are_blocked_but_different_years_remain_separate(self):
        reports = review([candidate(), candidate(60), candidate(65, year=2021)])
        self.assertEqual(reports['summary.json']['conflicting_scope_groups'], 1)
        self.assertEqual(reports['summary.json']['repeated_or_redundant_scope_rows'], 0)
        self.assertEqual(len(reports['variant-import-proposal.json']), 1)
        self.assertFalse(reports['variant-import-proposal.json'][0]['approved_for_import'])
        self.assertEqual(reports['scope-conflicts.json'][0]['fields']['tank_l'], [50, 60])
        self.assertEqual(reports['summary.json']['models_with_multiple_observed_values'], 1)

    def test_repeated_evidence_kept_without_duplicate_proposals_and_never_verified(self):
        result = review([candidate(), candidate(source_url='https://example.invalid/spec')])
        self.assertEqual(result['summary.json']['repeated_or_redundant_scope_rows'], 1)
        self.assertEqual(len(result['variant-import-proposal.json']), 1)
        self.assertEqual(len(result['provenance.json']), 2)
        self.assertEqual(result['summary.json']['approved_for_automatic_import'], 0)

    def test_battery_basis_not_confused_and_invalid_capacity_rejected(self):
        rows = [candidate(specifications={'batteri_kwh': 60}, battery_basis='usable'),
                candidate(specifications={'batteri_kwh': 65}, battery_basis='gross'), candidate(True)]
        result = review(rows)
        fields = result['variant-import-proposal.json'][0]['proposed_fields']
        self.assertEqual(fields, {'battery_usable_kwh': 60, 'battery_gross_kwh': 65})
        self.assertFalse(result['scope-conflicts.json'])
        self.assertEqual(len(result['rejected.json']), 1)
