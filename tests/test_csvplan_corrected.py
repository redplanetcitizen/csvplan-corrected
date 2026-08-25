from __future__ import annotations

import unittest

import numpy as np

from csvplan_corrected import legacy
from csvplan_corrected import solver as corrected


def toy_problem(*, zero_second_target: bool = False) -> corrected.PlanProblem:
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
    g = np.array([[10.0, 8.0], [10.0, 8.0], [10.0, 8.0]])
    if zero_second_target:
        g[:, 1] = 0.0
    return corrected.PlanProblem(
        headers=["Year", "p1", "p2", "Labour"],
        flows=np.zeros((4, 2)),
        caps=np.array([[100.0, 100.0], [100.0, 100.0]]),
        dep=dep,
        labtarg=np.zeros((3, 4)),
        A=A,
        C=C,
        D=D,
        leontief=np.linalg.inv(np.eye(3) - A),
        g=g,
        labouravailable=np.array([20.0, 20.0, 20.0]),
        years=np.array([1.0, 2.0, 3.0]),
        horizon=3,
        products=products,
    )


def evaluate_toy(problem=None):
    problem = problem or toy_problem()
    investments = np.zeros((problem.horizon, problem.products, problem.products))
    config = corrected.SolverConfig(strict=True, terminal_replacement=False)
    return corrected._evaluate(problem, investments, config)


class CorrectedSolverTests(unittest.TestCase):
    def test_flow_balance_known_solution(self):
        problem = toy_problem()
        lam, gross = corrected.max_consumption_scale(
            problem, problem.caps, np.zeros((2, 2)), 0
        )
        rhs = np.r_[lam * problem.g[0], 0.0]
        np.testing.assert_allclose(
            (np.eye(3) - problem.A) @ gross, rhs, rtol=1e-12, atol=1e-12
        )

    def test_direct_stock_recurrence_with_differentiated_rates(self):
        problem = toy_problem()
        investments = np.zeros((3, 2, 2))
        investments[0] = np.array([[3.0, 4.0], [5.0, 6.0]])
        investments[1] = np.array([[1.0, 2.0], [3.0, 4.0]])
        stock = corrected.propagate_stock(problem.caps, investments, problem.dep)
        expected1 = (1.0 - problem.dep) * problem.caps + investments[0]
        expected2 = (1.0 - problem.dep) * expected1 + investments[1]
        np.testing.assert_allclose(stock[1], expected1)
        np.testing.assert_allclose(stock[2], expected2)

    def test_inverse_depreciation_matches_forward_arrival(self):
        problem = toy_problem()
        desired = np.array([[9.0, 8.0], [7.0, 6.0]])
        source = corrected.inverse_depreciate(desired, 0, 2, problem.dep)
        arrived = source * np.power(1.0 - problem.dep, 1)
        np.testing.assert_allclose(arrived, desired)

    def test_zero_target_product_is_excluded_without_division_by_zero(self):
        scenario = evaluate_toy(toy_problem(zero_second_target=True))
        self.assertTrue(np.all(np.isnan(scenario.harmony_by_product[:, 1])))
        self.assertTrue(np.all(np.isfinite(scenario.h)))

    def test_negative_consumption_is_rejected(self):
        scenario = evaluate_toy()
        scenario.net_output[0, 0] = -1.0
        with self.assertRaises(corrected.ConstraintViolation):
            corrected.validate_scenario(scenario, strict=True)

    def test_labour_violation_is_rejected(self):
        scenario = evaluate_toy()
        scenario.O[0] *= 10.0
        with self.assertRaises(corrected.ConstraintViolation):
            corrected.validate_scenario(scenario, strict=True)

    def test_capital_violation_is_rejected(self):
        scenario = evaluate_toy()
        scenario.S[0] *= 0.001
        with self.assertRaises(corrected.ConstraintViolation):
            corrected.validate_scenario(scenario, strict=True)

    def test_flow_balance_violation_is_rejected(self):
        scenario = evaluate_toy()
        scenario.O[0, 0] += 1.0
        with self.assertRaises(corrected.ConstraintViolation):
            corrected.validate_scenario(scenario, strict=True)

    def test_terminal_equation_and_replacement_accounting(self):
        problem = toy_problem()
        replacement, q, _ = corrected.terminal_replacement(
            problem, problem.caps, 2, strict=False, tolerance=1e-10
        )
        gross = np.linalg.solve(
            np.eye(3) - problem.A - problem.D, np.r_[q * problem.g[2], 0.0]
        )
        np.testing.assert_allclose(
            replacement,
            problem.D[:2, :2] * gross[:2][None, :],
            rtol=1e-12,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            (np.eye(3) - problem.A - problem.D) @ gross,
            np.r_[q * problem.g[2], 0.0],
            rtol=1e-12,
            atol=1e-12,
        )

    def test_objective_is_strictly_monotone_on_real_data(self):
        result = corrected.run_default(
            config=corrected.SolverConfig(max_iterations=20, strict=False)
        )
        differences = np.diff(result["objective_history"])
        self.assertGreaterEqual(result["iterations"], 2)
        self.assertTrue(np.all(differences > 0.0))
        self.assertTrue(
            all(report.compliant for report in result["scenario"].constraint_report)
        )

    def test_legacy_and_corrected_outputs_document_expected_difference(self):
        legacy_result = legacy.run_default(False)
        corrected_result = corrected.run_default(
            config=corrected.SolverConfig(max_iterations=100, strict=False)
        )
        comparison = corrected.compare_with_legacy(corrected_result, legacy_result)
        self.assertEqual(comparison["years_compared"], 5)
        self.assertGreater(comparison["max_abs_net_output_difference"], 100_000.0)
        self.assertTrue(comparison["legacy_negative_outputs_hidden"])
        self.assertNotEqual(
            comparison["corrected_iterations"], comparison["legacy_iterations"]
        )
        self.assertTrue(np.all(corrected_result["scenario"].net_output >= -1e-8))


if __name__ == "__main__":
    unittest.main()
