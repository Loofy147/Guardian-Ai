import pandas as pd
import numpy as np
from guardian_ai.core.ski_rental import SkiRentalLAA
from guardian_ai.predictor.time_series import TimeSeriesPredictor

# --- Simulation Parameters ---
COMMIT_COST = 500  # Cost to "commit" (e.g., reserve a server)
STEP_COST = 10     # Cost per step (e.g., hourly on-demand cost)
TRUST_LEVEL = 0.8  # How much to trust the ML prediction (0 to 1)

import os

# --- Environment Configuration ---
# For security, the Hugging Face token is loaded from an environment variable.
# Before running the simulation, set the variable in your terminal:
# export HUGGING_FACE_TOKEN='your_hf_token_here'
HUGGING_FACE_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

def generate_sample_data(n_points=100, trend=0.1, seasonality=10, noise=5):
    """
    Generates a sample time series DataFrame.
    """
    time = np.arange(n_points)
    values = (time * trend +
              np.sin(time / 10) * seasonality +
              np.random.randn(n_points) * noise + 50)

    timestamps = pd.to_datetime(pd.date_range(start='2023-01-01', periods=n_points, freq='H'))

    return pd.DataFrame({'timestamp': timestamps, 'value': values})


def run_simulation():
    """
    Runs a full simulation of the SkiRentalLAA.
    """
    print("--- Starting Guardian AI Simulation ---")

    # 1. Generate historical data
    print("\n[Step 1] Generating sample historical data...")
    historical_data = generate_sample_data(n_points=200)
    print(f"Generated {len(historical_data)} data points.")

    # 2. Initialize the predictor
    print("\n[Step 2] Initializing the TimeSeriesPredictor...")
    # 2. Initialize the predictor
    print("\n[Step 2] Initializing the TimeSeriesPredictor...")
    if not HUGGING_FACE_TOKEN:
        print("Error: HUGGING_FACE_TOKEN environment variable not set.")
        print("Please set the variable: export HUGGING_FACE_TOKEN='your_hf_token_here'")
        return

    try:
        predictor = TimeSeriesPredictor(
            historical_demand=historical_data,
            token=HUGGING_FACE_TOKEN
        )
    except Exception as e:
        print(f"Error initializing predictor: {e}")
        return

    # 3. Initialize the Learning-Augmented Algorithm
    print("\n[Step 3] Initializing the SkiRentalLAA...")
    problem_params = {'commit_cost': COMMIT_COST, 'step_cost': STEP_COST}
    laa = SkiRentalLAA(predictor=predictor, problem_params=problem_params)

    # 4. Run the decision-making process
    print("\n[Step 4] Running the online decision-making process...")

    # Let's simulate a scenario where the actual duration is unknown in advance
    actual_duration = 60  # For example, a 60-hour usage period

    # Get a prediction before the period starts
    pred_duration, uncertainty = predictor.predict()
    print(f"ML Prediction: The expected duration is {pred_duration:.2f} hours (Uncertainty: +/- {uncertainty:.2f})")

    # Make decisions step-by-step
    final_action = "pay_as_you_go"
    for current_step in range(1, actual_duration + 1):
        action, guarantee = laa.decide(current_step, TRUST_LEVEL)
        print(f"  - Hour {current_step}: Recommendation is '{action}' (Worst-case guarantee: {guarantee:.2f}x optimal)")
        if action == "commit":
            final_action = "commit"
            print(f"  -> Decision to COMMIT made at hour {current_step}.")
            break

    if final_action == "pay_as_you_go":
        print("  -> Final Decision: Did not commit and paid as we went.")


    # 5. Analyze the outcome in hindsight
    print("\n[Step 5] Analyzing the outcome...")

    # Calculate costs
    algorithm_cost = laa._compute_algorithm_cost(actual_duration, TRUST_LEVEL)
    optimal_cost = laa._compute_optimal_cost(actual_duration)

    # Calculate competitive ratio
    competitive_ratio = laa.compute_competitive_ratio(actual_duration, TRUST_LEVEL)

    print(f"\n--- Simulation Results ---")
    print(f"Actual Duration: {actual_duration} hours")
    print(f"Trust Level in ML: {TRUST_LEVEL}")
    print("-" * 25)
    print(f"Cost of Our Algorithm: ${algorithm_cost:.2f}")
    print(f"Optimal Cost (in hindsight): ${optimal_cost:.2f}")
    print(f"Competitive Ratio: {competitive_ratio:.2f}")
    print(f"Theoretical Worst-Case Guarantee: {guarantee:.2f}")
    print("-" * 25)

    if competitive_ratio <= guarantee:
        print("✅ The algorithm performed within its worst-case guarantee.")
    else:
        print("❌ The algorithm did NOT perform within its guarantee. Needs review.")

    print("\n--- Simulation Complete ---")


if __name__ == "__main__":
    run_simulation()
