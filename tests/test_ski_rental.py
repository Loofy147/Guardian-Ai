import unittest
from unittest.mock import MagicMock
import pandas as pd

from guardian_ai.core.ski_rental import SkiRentalLAA
from guardian_ai.predictor.time_series import TimeSeriesPredictor

class TestSkiRentalLAA(unittest.TestCase):
    def setUp(self):
        self.problem_params = {'commit_cost': 100, 'step_cost': 10}
        self.dummy_df = pd.DataFrame({'timestamp': [pd.Timestamp.now()], 'value': [0]})

    def test_decide_commit(self):
        # Mock a predictor that returns a high prediction
        mock_predictor = TimeSeriesPredictor(
            token="dummy",
            historical_demand=self.dummy_df,
            prediction_override=15,
            uncertainty_override=1
        )
        laa = SkiRentalLAA(predictor=mock_predictor, problem_params=self.problem_params)
        action, _ = laa.decide(current_step=15, trust_level=0.8)
        self.assertEqual(action, "commit")

    def test_decide_pay_as_you_go(self):
        # Mock a predictor that returns a low prediction
        mock_predictor = TimeSeriesPredictor(
            token="dummy",
            historical_demand=self.dummy_df,
            prediction_override=5,
            uncertainty_override=1
        )
        laa = SkiRentalLAA(predictor=mock_predictor, problem_params=self.problem_params)
        action, _ = laa.decide(current_step=4, trust_level=0.8)
        self.assertEqual(action, "pay_as_you_go")

    def test_compute_threshold_low_uncertainty(self):
        mock_predictor = TimeSeriesPredictor(
            token="dummy",
            historical_demand=self.dummy_df,
            prediction_override=12,
            uncertainty_override=1
        )
        laa = SkiRentalLAA(predictor=mock_predictor, problem_params=self.problem_params)
        threshold = laa._compute_threshold(pred=12, uncertainty=1, trust=0.8)
        self.assertEqual(threshold, 12)

    def test_compute_threshold_high_uncertainty(self):
        mock_predictor = TimeSeriesPredictor(
            token="dummy",
            historical_demand=self.dummy_df,
            prediction_override=12,
            uncertainty_override=5
        )
        laa = SkiRentalLAA(predictor=mock_predictor, problem_params=self.problem_params)
        threshold = laa._compute_threshold(pred=12, uncertainty=5, trust=0.8)
        # classical = 100 / 10 = 10
        # blended = (1 - 0.8) * 10 + 0.8 * 12 = 2 + 9.6 = 11.6
        self.assertAlmostEqual(threshold, 11.6, places=1)

    def test_compute_algorithm_cost_commit(self):
        mock_predictor = TimeSeriesPredictor(
            token="dummy",
            historical_demand=self.dummy_df,
            prediction_override=15, # High prediction, leads to commit
            uncertainty_override=1
        )
        laa = SkiRentalLAA(predictor=mock_predictor, problem_params=self.problem_params)
        # Threshold will be 15
        cost = laa._compute_algorithm_cost(actual_duration=16, trust_level=0.8)
        # Cost = (15 - 1) * 10 + 100 = 140 + 100 = 240
        self.assertEqual(cost, 240)

    def test_compute_algorithm_cost_pay_as_you_go(self):
        mock_predictor = TimeSeriesPredictor(
            token="dummy",
            historical_demand=self.dummy_df,
            prediction_override=5, # Low prediction, leads to pay_as_you_go
            uncertainty_override=1
        )
        laa = SkiRentalLAA(predictor=mock_predictor, problem_params=self.problem_params)
        # Threshold will be 5
        cost = laa._compute_algorithm_cost(actual_duration=4, trust_level=0.8)
        # Cost = 4 * 10 = 40
        self.assertEqual(cost, 40)

    def test_compute_optimal_cost_commit(self):
        laa = SkiRentalLAA(predictor=None, problem_params=self.problem_params)
        cost = laa._compute_optimal_cost(actual_duration=12)
        # Optimal cost is commit_cost = 100
        self.assertEqual(cost, 100)

    def test_compute_optimal_cost_pay_as_you_go(self):
        laa = SkiRentalLAA(predictor=None, problem_params=self.problem_params)
        cost = laa._compute_optimal_cost(actual_duration=8)
        # Optimal cost is 8 * 10 = 80
        self.assertEqual(cost, 80)

    def test_commit_cost_with_float_threshold(self):
        """
        Tests that the algorithm cost is calculated correctly when the threshold
        is a float. The cost should be based on the ceiling of the threshold.
        """
        mock_predictor = TimeSeriesPredictor(
            token="dummy",
            historical_demand=self.dummy_df,
            prediction_override=7, # pred=7 -> threshold=7.6
            uncertainty_override=5 # High uncertainty to trigger blended threshold
        )
        laa = SkiRentalLAA(predictor=mock_predictor, problem_params=self.problem_params)
        # classical=10, blended = 0.2*10 + 0.8*7 = 2 + 5.6 = 7.6
        cost = laa._compute_algorithm_cost(actual_duration=12, trust_level=0.8)

        # The algorithm commits at step ceil(7.6) = 8.
        # Cost = (8 - 1) * 10 (pay-as-you-go) + 100 (commit) = 70 + 100 = 170
        self.assertEqual(cost, 170)


if __name__ == '__main__':
    unittest.main()
