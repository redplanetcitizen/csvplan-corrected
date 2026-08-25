import unittest

import numpy as np

from csvplan_corrected import legacy


class LegacyRegressionTests(unittest.TestCase):
    def test_legacy_reproduces_verified_julia_reference(self):
        result = legacy.run_default(False)
        scenario = result["scenario"]
        self.assertEqual(result["iterations"], 811)
        self.assertEqual(result["stop_reason"], "no_transfer")
        self.assertTrue(
            np.isclose(scenario.meanh, 0.4835942427893382, rtol=0.0, atol=3e-15)
        )
        self.assertTrue(
            np.isclose(scenario.stdh, 0.023616715497360313, rtol=0.0, atol=3e-15)
        )
        np.testing.assert_allclose(
            scenario.h[:5],
            [
                0.45272152656618436,
                0.46619784828623845,
                0.48040106141394195,
                0.4983165290857051,
                0.4935714018948021,
            ],
            rtol=2e-14,
            atol=2e-14,
        )


if __name__ == "__main__":
    unittest.main()
