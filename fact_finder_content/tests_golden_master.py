"""
Tests for the golden-master pre-publish validation gate (fact_finder_content/golden_master.py).

Uses SimpleTestCase since this module only reads static fixture files and
does not touch the database.
"""
from django.test import SimpleTestCase

from fact_finder_content.golden_master import (
    evaluate_display_condition,
    load_golden_master_cases,
)


class LoadGoldenMasterCasesTests(SimpleTestCase):
    def test_loads_all_24_cases(self):
        cases = load_golden_master_cases()
        self.assertEqual(len(cases), 24)

    def test_every_case_has_a_validated_contract_with_expected_top_level_keys(self):
        cases = load_golden_master_cases()
        for case in cases:
            contract = case['contract']
            self.assertIn('system', contract)
            self.assertIn('computed_flags', contract)
            self.assertIsInstance(case['emp_id'], int)
            self.assertTrue(case['label'])

    def test_known_case_has_expected_system_type_and_retirement_type(self):
        cases = {c['emp_id']: c['contract'] for c in load_golden_master_cases()}
        self.assertEqual(cases[42293]['system']['system_type'], 'FERS')
        self.assertEqual(cases[42293]['system']['retirement_type'], 'Deferred')
        self.assertEqual(cases[36798]['system']['system_type'], 'CSRS')
        self.assertEqual(cases[34971]['system']['system_type'], 'Transfers')

    def test_result_is_cached_across_calls(self):
        # lru_cache means the exact same list object comes back (not just equal
        # contents) — verifies we're not re-reading 24 files from disk on every call.
        self.assertIs(load_golden_master_cases(), load_golden_master_cases())


class EvaluateDisplayConditionTests(SimpleTestCase):
    def test_none_condition_matches_all_24_cases(self):
        results = evaluate_display_condition(None)
        self.assertEqual(len(results), 24)
        self.assertTrue(all(r['matches'] for r in results))
        self.assertTrue(all(r['error'] is None for r in results))

    def test_empty_rules_condition_matches_all_24_cases(self):
        results = evaluate_display_condition({'rules': []})
        self.assertTrue(all(r['matches'] for r in results))

    def test_retirement_type_deferred_matches_exactly_the_5_known_deferred_cases(self):
        condition = {'rules': [
            {'field': 'system.retirement_type', 'operator': 'equals', 'value': 'Deferred'},
        ]}
        results = evaluate_display_condition(condition)
        matching_ids = {r['emp_id'] for r in results if r['matches']}
        # Verified directly against the fixture JSON: exactly these 5 of the
        # 24 golden-master cases have retirement_type == 'Deferred'.
        self.assertEqual(matching_ids, {42293, 31853, 42210, 19833, 35789})

    def test_is_wep_applicable_matches_exactly_the_3_known_wep_cases(self):
        condition = {'rules': [
            {'field': 'computed_flags.is_wep_applicable', 'operator': 'equals', 'value': True},
        ]}
        results = evaluate_display_condition(condition)
        matching_ids = {r['emp_id'] for r in results if r['matches']}
        self.assertEqual(matching_ids, {30257, 36798, 41444})

    def test_results_preserve_manifest_order(self):
        results = evaluate_display_condition(None)
        emp_ids_in_order = [r['emp_id'] for r in results]
        self.assertEqual(emp_ids_in_order[0], 42293)  # first entry in manifest.json

    def test_every_result_has_expected_shape(self):
        results = evaluate_display_condition(None)
        for r in results:
            self.assertEqual(set(r.keys()), {'emp_id', 'label', 'matches', 'error'})
