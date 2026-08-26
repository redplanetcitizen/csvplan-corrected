from __future__ import annotations

import unittest

import numpy as np

from csvplan_corrected import legacy
from csvplan_corrected import reconciled


class ReconciledAppendixARegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = reconciled.default_data_paths()
        cls.result = reconciled.run_default()

    def test_loader_appends_documented_repeat_last_shadow_horizon(self):
        headers, _, _, _, labtarg = legacy.readinspreadsheets(*self.paths)
        problem = legacy.readInProblem(*self.paths)
        explicit_years = labtarg.shape[0]
        shadow_years = legacy.DEPRECIATION_HORIZON

        self.assertEqual(shadow_years, 14)
        self.assertEqual(problem.TheLastYear, explicit_years + shadow_years)

        expected_targets = np.repeat(
            labtarg[-1, 1 : len(headers) - 1][None, :],
            shadow_years,
            axis=0,
        )
        np.testing.assert_allclose(
            problem.g[explicit_years:, :-1],
            expected_targets,
            rtol=0.0,
            atol=0.0,
        )
        np.testing.assert_allclose(
            problem.labouravailable[explicit_years:],
            np.full(shadow_years, labtarg[-1, -1]),
            rtol=0.0,
            atol=0.0,
        )

    def test_result_separates_published_and_shadow_horizons(self):
        self.assertEqual(
            self.result["computational_horizon"],
            self.result["published_horizon"] + legacy.DEPRECIATION_HORIZON,
        )
        self.assertEqual(len(self.result["annual"]), self.result["published_horizon"])
        self.assertEqual(
            len(self.result["shadow_annual"]), legacy.DEPRECIATION_HORIZON
        )

    def test_no_transfer_is_a_valid_structured_termination(self):
        self.assertEqual(self.result["stop_reason"], "no_transfer")
        self.assertGreater(self.result["accepted_moves"], 0)
        self.assertEqual(
            self.result["attempts"], self.result["accepted_moves"] + 1
        )

    def test_appendix_a_provenance_is_machine_visible(self):
        provenance = self.result["provenance"]
        self.assertEqual(
            provenance["continuation_source_status"], "explicit_text_rule"
        )
        self.assertEqual(provenance["depreciation_horizon"], 14)
        self.assertEqual(
            provenance["depreciation_horizon_source_status"],
            "explicit_text_default_parameter",
        )
        self.assertEqual(
            provenance["destination_source_status"],
            "textual_conflict_formalized_choice",
        )


if __name__ == "__main__":
    unittest.main()
