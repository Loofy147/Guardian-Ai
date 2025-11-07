from .base import LearningAugmentedAlgorithm


class SkiRentalLAA(LearningAugmentedAlgorithm):
    """
    For problems where you commit resources vs. pay-as-you-go.
    """

    def decide(self, current_step, trust_level):
        # Get prediction
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
        Computes the cost of the decision made by the LAA.
        """
        pred_duration, uncertainty = self.predictor.predict()
        threshold = self._compute_threshold(pred_duration, uncertainty, trust_level)

        # The algorithm commits if the actual duration exceeds the threshold
        if actual_duration >= threshold:
            # We decided to commit at the threshold point
            cost = threshold * self.params['step_cost'] + self.params['commit_cost']
        else:
            # We paid as we went for the full duration
            cost = actual_duration * self.params['step_cost']

        # However, the ski-rental problem implies a single decision point.
        # Let's refine the logic to reflect the online nature of the problem.
        # The decision is made at each step.
        cost = 0
        committed = False
        for step in range(1, int(actual_duration) + 1):
            action, _ = self.decide(step, trust_level)
            if action == "commit":
                cost += self.params['commit_cost']
                committed = True
                break
            else:
                cost += self.params['step_cost']

        if committed:
            # if we committed, the cost is the pay-as-you-go cost up to that point, plus the commit cost
            # let's find the point of commitment
            commit_step = 0
            for step in range(1, int(actual_duration) + 2):
                 action, _ = self.decide(step, trust_level)
                 if action == "commit":
                     commit_step = step
                     break
            cost = (commit_step -1) * self.params['step_cost'] + self.params['commit_cost']
        else:
            cost = actual_duration * self.params['step_cost']
        return min(cost, actual_duration * self.params['step_cost'])


    def _compute_optimal_cost(self, actual_duration):
        """
        Computes the optimal offline cost in hindsight.
        """
        pay_as_you_go_cost = actual_duration * self.params['step_cost']
        commit_cost = self.params['commit_cost']
        return min(pay_as_you_go_cost, commit_cost)
