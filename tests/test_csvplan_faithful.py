from __future__ import annotations

import unittest

import numpy as np

from csvplan_corrected import faithful
from csvplan_corrected import solver


def toy_problem() -> solver.PlanProblem:
    products = 2
    A = np.array(
        [[0.10, 0.02, 0.0], [0.05, 0.15, 0.0], [0.40, 0.30, 0.0]],
        dtype=float,
    )
    C = np.zeros((3, 3), dtype=float)
    C[:2, :2] = np.array([[0.8, 0.2], [0.1, 0.6]])
    dep = np.array([[0.10, 0.20], [0.25, 0.50]])
    D = np.zeros_like(C)
    D[:2, :2] = C[:2, :2] * dep
    g = np.array([[10.0, 8.0], [11.0, 8.5], [12.0, 9.0]])
    labour = np.array([20.0, 21.0, 22.0])
    years = np.array([2020.0, 2021.0, 2022.0])
    return solver.PlanProblem(
        headers=["Year", "p1", "p2", "Labour"],
        flows=np.zeros((4, 2)),
        caps=np.array([[100.0, 100.0], [100.0, 100.0]]),
        dep=dep,
        labtarg=np.column_stack([years, g, labour]),
        A=A,
        C=C,
        D=D,
        leontief=np.linalg.inv(np.eye(3) - A),
        g=g,
        labouravailable=labour,
        years=years,
        horizon=3,
        products=products,
    )


class FaithfulControllerTests(unittest.TestCase):
    def test_default_epsilon_matches_julia_operational_value(self):
        config = faithful.FaithfulConfig(depreciation_horizon=14)
        self.assertAlmostEqual(config.resolved_epsilon(), 0.25 / 14.0)

    def test_stationary_horizon_extension_repeats_last_target_and_labour(self):
        problem = toy_problem()
        extended, published = faithful.extend_stationary_horizon(problem, 4)
        self.assertEqual(published, 3)
        self.assertEqual(extended.horizon, 7)
        np.testing.assert_allclose(
            extended.g[3:],
            np.repeat(problem.g[-1:, :], 4, axis=0),
        )
        np.testing.assert_allclose(
            extended.labouravailable[3:],
            np.repeat(problem.labouravailable[-1:], 4),
        )
        np.testing.assert_allclose(extended.years, np.arange(2020.0, 2027.0))

    def test_faithful_default_exposes_published_and_computational_horizons(self):
        result = faithful.run_default(
            config=faithful.FaithfulConfig(
                max_iterations=0,
                terminal_replacement=False,
                strict=False,
            )
        )
        self.assertEqual(result["published_horizon"], 5)
        self.assertEqual(result["computational_horizon"], 19)
        self.assertEqual(len(result["annual"]), 5)
        self.assertEqual(len(result["shadow_annual"]), 14)
        self.assertAlmostEqual(result["epsilon"], 0.25 / 14.0)

    def test_accepted_changes_use_one_fixed_epsilon_and_are_monotone(self):
        result = faithful.run_default(
            config=faithful.FaithfulConfig(
                max_iterations=10,
                terminal_replacement=False,
                strict=False,
            )
        )
        steps = result["accepted_steps"]
        if steps:
            self.assertTrue(
                all(abs(step["epsilon"] - result["epsilon"]) <= 1e-15 for step in steps)
            )
            self.assertTrue(np.all(np.diff(result["objective_history"]) > 0.0))
            self.assertTrue(
                all(step["source_year"] < step["destination_year"] for step in steps)
            )


if __name__ == "__main__":
    unittest.main()
