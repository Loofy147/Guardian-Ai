from .base import LearningAugmentedAlgorithm


class SkiRentalLAA(LearningAugmentedAlgorithm):
    """
    For problems where you commit resources vs. pay-as-you-go.
    """

    def decide(self, current_step, trust_level):
        # Get prediction from the initialized predictor
        pred_duration, uncertainty = self.predictor.predict()

        # Compute threshold
        threshold = self._compute_threshold(
            pred_duration,
            uncertainty,
            trust_level
        )

        # Make decision
        if current_step >= threshold:
            action = "commit"
        else:
            action = "pay_as_you_go"

        # Compute guarantee
        guarantee = (1 + trust_level) / trust_level

        return action, guarantee

    def _compute_threshold(self, pred, uncertainty, trust):
        # Classical threshold
        classical = self.params['commit_cost'] / self.params['step_cost']

        # ML-informed threshold
        ml_threshold = pred

        # Blend based on uncertainty
        if uncertainty > pred * 0.2:  # High uncertainty
            return (1 - trust) * classical + trust * ml_threshold
        else:  # Low uncertainty, trust ML more
            return ml_threshold

    def _compute_algorithm_cost(self, actual_duration, trust_level):
        """
        Computes the cost of the decision made by the LAA based on a given outcome.
        This method calculates the cost without re-running the decision process.
        """
        pred_duration, uncertainty = self.predictor.predict()
        threshold = self._compute_threshold(pred_duration, uncertainty, trust_level)

        if actual_duration >= threshold:
            # If the actual duration meets or exceeds the threshold, the algorithm
            # would have committed. The cost is the pay-as-you-go cost up to the
            # threshold, plus the commit cost.
            cost = (threshold - 1) * self.params['step_cost'] + self.params['commit_cost']
        else:
            # If the actual duration is less than the threshold, the algorithm
            # would have paid as it went for the full duration.
            cost = actual_duration * self.params['step_cost']

        return cost


    def _compute_optimal_cost(self, actual_duration):
        """
        Computes the optimal offline cost in hindsight.
        """
        pay_as_you_go_cost = actual_duration * self.params['step_cost']
        commit_cost = self.params['commit_cost']
        return min(pay_as_you_go_cost, commit_cost)
