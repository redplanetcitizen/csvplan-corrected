from __future__ import annotations

import unittest

import numpy as np

from csvplan_corrected import legacy, reconciled


class ReconciledReferenceTests(unittest.TestCase):
    def test_reference_profile_emits_all_adjudicated_provenance(self):
        cfg = reconciled.ReconciledConfig()
        cfg.validate()
        p = cfg.provenance()
        self.assertEqual(p["profile"], "reference_reconciled")
        self.assertEqual(p["warm_start_policy"], "historical_matrix_warm_start")
        self.assertEqual(p["warm_start_source_status"], "code_only_boundary_condition")
        self.assertEqual(p["warm_start_stock_timing"], "exact_recurrence")
        self.assertEqual(p["continuation_policy"], "repeat_last")
        self.assertEqual(p["epsilon_policy"], "historical_matrix")
        self.assertAlmostEqual(p["epsilon"], 0.25 / 14.0)
        self.assertEqual(p["capital_update_policy"], "historical_matrix_specialization")
        self.assertEqual(p["capital_update_source_status"], "historical_matrix_specialization")
        self.assertEqual(p["blocked_destination_policy"], "historical_first_blocked")
        self.assertEqual(p["destination_policy"], "global_lowest_harmony")
        self.assertEqual(p["depreciation_timing"], "exact_stock_recurrence")
        self.assertEqual(p["robust_harmony"], "minimum_all_positive_target_products")

    def test_reference_warm_start_obeys_exact_stock_recurrence(self):
        cfg = reconciled.ReconciledConfig()
        s, published = reconciled._build_initial(*legacy.default_data_paths(), cfg)
        self.assertEqual(published, 5)
        preliminary = cfg.warm_start_level * (s.prob.caps * s.prob.dep)
        expected_year_2 = (1.0 - s.prob.dep) * s.prob.caps + preliminary
        np.testing.assert_allclose(s.si[1], expected_year_2, rtol=0.0, atol=1.0e-9)

    def test_reference_default_reproduces_audited_exact_timing_checkpoint(self):
        result = reconciled.run_default()
        self.assertEqual(result["published_horizon"], 5)
        self.assertEqual(result["computational_horizon"], 19)
        self.assertEqual(result["accepted_moves"], 41)
        self.assertEqual(result["attempts"], 42)
        self.assertEqual(result["stop_reason"], "no_transfer")
        self.assertEqual(result["negative_net_output_cells"], 0)
        self.assertAlmostEqual(result["mean_harmony"], 0.49376756432817903, places=12)
        self.assertAlmostEqual(result["coefficient_of_variation"], 0.04185397966020812, places=12)
        self.assertAlmostEqual(result["min_harmony"], 0.42113900177214186, places=12)

    def test_reference_begins_with_global_lowest_harmony_and_earlier_source(self):
        result = reconciled.run_default()
        initial = np.asarray(result["initial_harmony"])
        first = next(row for row in result["trace"] if row["accepted"])
        self.assertEqual(first["destination_year"], int(np.argmin(initial)))
        self.assertLess(first["source_year"], first["destination_year"])
        accepted = [row for row in result["trace"] if row["accepted"]]
        self.assertTrue(all(row["mean_after"] > row["mean_before"] for row in accepted))

    def test_ranked_full_pass_is_labelled_as_our_choice(self):
        cfg = reconciled.ReconciledConfig(blocked_destination_policy="ranked_full_pass")
        p = cfg.provenance()
        self.assertEqual(p["blocked_destination_source_status"], "our_choice_completion_rule")

    def test_text_epsilon_is_a_named_suggestion_not_default(self):
        historical = reconciled.ReconciledConfig().resolved_epsilon()
        suggested = reconciled.ReconciledConfig(
            epsilon_policy="text_first_suggestion"
        ).resolved_epsilon()
        self.assertAlmostEqual(historical, 1.0 / 56.0)
        self.assertAlmostEqual(suggested, 1.0 / 15.0)
        self.assertNotEqual(historical, suggested)


if __name__ == "__main__":
    unittest.main()
