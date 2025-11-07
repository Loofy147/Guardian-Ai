from fastapi import FastAPI, HTTPException
from pantic import BaseModel
import pandas as pd
import os
from guardian_ai.core.ski_rental import SkiRentalLAA
from guardian_ai.predictor.time_series import TimeSeriesPredictor
# --- App Initialization ---
app = FastAPI(
    title="Guardian AI",
    description="A decision support platform for online optimization problems.",
    version="0.1.0",
)
# --- Environment ---
HUGGING_FACE_TOKEN = os.getenv("HUGGING_FACE_TOKEN")
if not HUGGING_FACE_TOKEN:
    raise RuntimeError("HUGGING_FACE_TOKEN environment variable not set.")
# --- API Models ---
class HealthResponse(BaseModel):
    status: str
class DecisionRequest(BaseModel):
    problem_type: str
    historical_data: list[dict]  # e.g., [{'timestamp': '2023-01-01', 'value': 123.4}]
    problem_params: dict         # e.g., {'commit_cost': 500, 'step_cost': 10}
    decision_state: dict         # e.g., {'current_step': 25}
    trust_level: float = 0.8
class DecisionResponse(BaseModel):
    action: str
    guarantee: float
    prediction: float
    uncertainty: float
# --- API Endpoints ---
@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint to confirm the service is running.
    """
    return {"status": "healthy"}
@app.post("/decide", response_model=DecisionResponse)
async def make_decision(request: DecisionRequest):
    """
    Main endpoint to get a decision from a Learning-Augmented Algorithm.
    """
    if request.problem_type != "ski_rental":
        raise HTTPException(status_code=400, detail="Problem type not supported.")
    # Convert historical data to a DataFrame
    try:
        historical_df = pd.DataFrame(request.historical_data)
        historical_df['timestamp'] = pd.to_datetime(historical_df['timestamp'])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid historical data format: {e}")
    # Initialize the predictor with the provided historical data
    try:
        predictor = TimeSeriesPredictor(
            token=HUGGING_FACE_TOKEN,
            historical_demand=historical_df
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing predictor: {e}")
    # Initialize the LAA with the now-functional predictor
    laa = SkiRentalLAA(predictor=predictor, problem_params=request.problem_params)
    # Get the prediction and uncertainty for the response
    prediction, uncertainty = predictor.predict()
    # Make the decision
    action, guarantee = laa.decide(
        current_step=request.decision_state.get('current_step', 1),
        trust_level=request.trust_level
    )
    return DecisionResponse(
        action=action,
        guarantee=guarantee,
        prediction=prediction,
        uncertainty=uncertainty,
    )
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
