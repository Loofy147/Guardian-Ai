"""
This module defines the base class for Learning-Augmented Algorithms (LAAs).
"""


class LearningAugmentedAlgorithm:
    """
    Base class for all LAAs.
    Each problem inherits and implements specific logic.
    """

    def __init__(self, predictor, problem_params):
        self.predictor = predictor
        self.params = problem_params

    def decide(self, state, trust_level):
        """
        Main decision function.

        Returns:
            action: str - The action to take
            guarantee: float - Worst-case competitive ratio
        """
        raise NotImplementedError

    def compute_competitive_ratio(self, actual_outcome, trust_level):
        """
        Computes competitive ratio for this instance.

        CR = cost_of_algorithm / cost_of_optimal_offline
        """
        alg_cost = self._compute_algorithm_cost(actual_outcome, trust_level)
        opt_cost = self._compute_optimal_cost(actual_outcome)
        if opt_cost == 0:
            return float('inf') if alg_cost > 0 else 1.0
        return alg_cost / opt_cost

    def _compute_algorithm_cost(self, outcome, trust_level):
        raise NotImplementedError

    def _compute_optimal_cost(self, outcome):
        raise NotImplementedError
