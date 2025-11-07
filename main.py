from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import pandas as pd
import os
import uuid
from sqlalchemy.orm import Session

from guardian_ai.core.ski_rental import SkiRentalLAA
from guardian_ai.predictor.time_series import TimeSeriesPredictor
from guardian_ai.database import create_db_and_tables, SessionLocal, Problem, Prediction, Decision

# --- App Initialization ---
app = FastAPI(
    title="Guardian AI",
    description="A decision support platform for online optimization problems.",
    version="0.1.0",
)

# --- Environment ---
HUGGING_FACE_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

# --- Database Session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    """
    On startup, check for the Hugging Face token and create the database and tables.
    """
    print("Creating database and tables...")
    create_db_and_tables()
    print("Database and tables created successfully.")

    if not HUGGING_FACE_TOKEN:
        raise RuntimeError("HUGGING_FACE_TOKEN environment variable not set.")

# --- API Models ---
class HealthResponse(BaseModel):
    status: str

class DecisionRequest(BaseModel):
    user_id: uuid.UUID
    problem_type: str
    historical_data: list[dict]
    problem_params: dict
    decision_state: dict
    trust_level: float = 0.8

class DecisionResponse(BaseModel):
    action: str
    guarantee: float
    prediction: float
    uncertainty: float
    problem_id: uuid.UUID
    decision_id: uuid.UUID

# --- API Endpoints ---
@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint to confirm the service is running.
    """
    return {"status": "healthy"}

@app.post("/decide", response_model=DecisionResponse)
async def make_decision(request: DecisionRequest, db: Session = Depends(get_db)):
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

    # Initialize the predictor
    try:
        predictor = TimeSeriesPredictor(
            token=HUGGING_FACE_TOKEN,
            historical_demand=historical_df
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing predictor: {e}")

    # Get prediction and uncertainty
    prediction_val, uncertainty_val = predictor.predict()

    # Create a new problem record in the database
    db_problem = Problem(
        user_id=request.user_id,
        problem_type=request.problem_type,
        config=request.problem_params
    )
    db.add(db_problem)
    db.commit()
    db.refresh(db_problem)

    # Create a new prediction record
    db_prediction = Prediction(
        problem_id=db_problem.id,
        predicted_value=prediction_val,
        uncertainty=uncertainty_val,
        trust_level=request.trust_level
    )
    db.add(db_prediction)
    db.commit()
    db.refresh(db_prediction)

    # Initialize the LAA
    laa = SkiRentalLAA(predictor=predictor, problem_params=request.problem_params)
    action, guarantee = laa.decide(
        current_step=request.decision_state.get('current_step', 1),
        trust_level=request.trust_level
    )

    # Create a new decision record
    db_decision = Decision(
        problem_id=db_problem.id,
        prediction_id=db_prediction.id,
        action=action
    )
    db.add(db_decision)
    db.commit()
    db.refresh(db_decision)

    return DecisionResponse(
        action=action,
        guarantee=guarantee,
        prediction=prediction_val,
        uncertainty=uncertainty_val,
        problem_id=db_problem.id,
        decision_id=db_decision.id,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
