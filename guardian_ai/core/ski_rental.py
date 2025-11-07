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
        Computes the cost incurred by the LAA's decisions given the actual outcome.
        """
        # The predictor is already initialized with historical data, so we can get a
        # prediction without passing the data again.
        pred_duration, uncertainty = self.predictor.predict()

        # Determine the decision threshold based on the prediction
        threshold = self._compute_threshold(pred_duration, uncertainty, trust_level)

        # Find the point at which the algorithm would have committed
        commit_step = -1
        for step in range(1, int(actual_duration) + 1):
            if step >= threshold:
                commit_step = step
                break

        if commit_step != -1:
            # The algorithm decided to commit.
            # The cost is the pay-as-you-go cost up to the commitment point,
            # plus the flat commit cost.
            cost = (commit_step - 1) * self.params['step_cost'] + self.params['commit_cost']
        else:
            # The algorithm never committed, so it paid the step cost for the full duration.
            cost = actual_duration * self.params['step_cost']

        return cost


    def _compute_optimal_cost(self, actual_duration):
        """
        Computes the optimal offline cost in hindsight.
        """
        pay_as_you_go_cost = actual_duration * self.params['step_cost']
        commit_cost = self.params['commit_cost']
        return min(pay_as_you_go_cost, commit_cost)
