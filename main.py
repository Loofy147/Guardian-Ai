from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import pandas as pd
import os
import uuid
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from guardian_ai.core.ski_rental import SkiRentalLAA
from guardian_ai.auth import (
    Token,
    User,
    get_current_user,
    create_access_token,
    verify_password,
    User,
    get_current_user,
    create_access_token,
    verify_password,
    get_user,
    create_user,
    UserInDB,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from guardian_ai.predictor.time_series import TimeSeriesPredictor
from guardian_ai.database import create_db_and_tables, SessionLocal, Problem, Prediction, Decision
from guardian_ai.worker import long_running_task
from celery.result import AsyncResult
import redis

# --- App Initialization ---
app = FastAPI(
    title="Guardian AI",
    description="A decision support platform for online optimization problems.",
    version="0.1.0",
)

# --- Environment ---
HUGGING_FACE_TOKEN = os.getenv("HUGGING_FACE_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# --- Caching ---
cache = redis.from_url(REDIS_URL)

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
    On startup, create the database and a default user.
    """
    create_db_and_tables()
    db = SessionLocal()
    # Create a default user if it doesn't exist
    if not get_user(db, "guardian_user"):
        create_user(db, UserInDB(
            username="guardian_user",
            email="user@example.com",
            full_name="Guardian User",
            hashed_password="secretpassword" # This will be hashed by create_user
        ))
    db.close()

    if not HUGGING_FACE_TOKEN:
        raise RuntimeError("HUGGING_FACE_TOKEN environment variable not set.")

# --- API Models ---
class HealthResponse(BaseModel):
    status: str

class DecisionRequest(BaseModel):
    user_id: uuid.UUID
    problem_id: Optional[uuid.UUID] = None
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

class LogOutcomeRequest(BaseModel):
    decision_id: uuid.UUID
    actual_outcome: float

class LogOutcomeResponse(BaseModel):
    message: str
    decision_id: uuid.UUID
    actual_outcome: float
    algorithm_cost: float
    optimal_cost: float

class PerformanceMetrics(BaseModel):
    total_decisions: int
    total_cost_algorithm: float
    total_cost_optimal: float
    total_savings: float
    average_competitive_ratio: float
    decisions_within_guarantee: int

class PerformanceResponse(BaseModel):
    problem_id: uuid.UUID
    problem_type: str
    metrics: PerformanceMetrics

# --- API Endpoints ---
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint to confirm the service is running.
    """
    return {"status": "healthy"}

@app.post("/decide", response_model=DecisionResponse)
async def make_decision(request: DecisionRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Main endpoint to get a decision from a Learning-Augmented Algorithm.
    """
    if request.problem_type != "ski_rental":
        raise HTTPException(status_code=400, detail="Problem type not supported.")

    if not request.historical_data:
        raise HTTPException(status_code=400, detail="No historical data provided to make a prediction.")

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

    # Find or create the problem
    if request.problem_id:
        db_problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
        if not db_problem:
            raise HTTPException(status_code=404, detail="Problem not found.")
    else:
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

@app.post("/log_outcome", response_model=LogOutcomeResponse)
async def log_outcome(request: LogOutcomeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Logs the actual outcome of a decision, allowing for performance tracking.
    """
    db_decision = db.query(Decision).filter(Decision.id == request.decision_id).first()
    if not db_decision:
        raise HTTPException(status_code=404, detail="Decision not found.")

    db_problem = db_decision.problem
    db_prediction = db_decision.prediction

    if not db_problem or not db_prediction:
        raise HTTPException(status_code=404, detail="Associated problem or prediction not found.")

    # Re-instantiate the predictor with the *original* prediction to ensure
    # the cost calculation uses the same information the decision was based on.
    # We pass a dummy historical_demand as it won't be used.
    dummy_df = pd.DataFrame({'timestamp': [pd.Timestamp.now()], 'value': [0]})
    predictor = TimeSeriesPredictor(
        token=HUGGING_FACE_TOKEN,
        historical_demand=dummy_df,
        prediction_override=db_prediction.predicted_value,
        uncertainty_override=db_prediction.uncertainty
    )

    # Re-instantiate the LAA
    laa = SkiRentalLAA(predictor=predictor, problem_params=db_problem.config)

    # Calculate costs in hindsight
    algorithm_cost = laa._compute_algorithm_cost(request.actual_outcome, db_prediction.trust_level)
    optimal_cost = laa._compute_optimal_cost(request.actual_outcome)

    # Update the decision record with the outcome and costs
    db_decision.actual_outcome = request.actual_outcome
    db_decision.cost = algorithm_cost
    db_decision.optimal_cost = optimal_cost
    db.commit()

    return LogOutcomeResponse(
        message="Outcome logged and performance calculated successfully.",
        decision_id=request.decision_id,
        actual_outcome=request.actual_outcome,
        algorithm_cost=algorithm_cost,
        optimal_cost=optimal_cost
    )

@app.post("/tasks/long_running")
async def run_long_task():
    task = long_running_task.delay(1, 2)
    return {"task_id": task.id}

@app.get("/tasks/status/{task_id}")
async def get_task_status(task_id: str):
    task_result = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result,
        "info": task_result.info,
    }

@app.get("/performance/{problem_id}", response_model=PerformanceResponse)
async def get_performance(problem_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieves and calculates performance metrics for a given problem, with caching.
    """
    # Check cache first
    cached_performance = cache.get(f"performance:{problem_id}")
    if cached_performance:
        return PerformanceResponse.parse_raw(cached_performance)

    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found.")

    decisions = problem.decisions
    completed_decisions = [d for d in decisions if d.cost is not None and d.optimal_cost is not None]

    if not completed_decisions:
        raise HTTPException(status_code=404, detail="No completed decisions found for this problem.")

    total_cost_algorithm = sum(d.cost for d in completed_decisions)
    total_cost_optimal = sum(d.optimal_cost for d in completed_decisions)
    total_savings = total_cost_optimal - total_cost_algorithm

    competitive_ratios = [(d.cost / d.optimal_cost) if d.optimal_cost > 0 else 1.0 for d in completed_decisions]
    average_competitive_ratio = sum(competitive_ratios) / len(competitive_ratios)

    # This is a simplified guarantee check. A more robust implementation would store
    # the guarantee for each decision.
    decisions_within_guarantee = sum(1 for cr in competitive_ratios if cr <= 2.25) # Using the default guarantee

    metrics = PerformanceMetrics(
        total_decisions=len(completed_decisions),
        total_cost_algorithm=total_cost_algorithm,
        total_cost_optimal=total_cost_optimal,
        total_savings=total_savings,
        average_competitive_ratio=average_competitive_ratio,
        decisions_within_guarantee=decisions_within_guarantee,
    )

    response = PerformanceResponse(
        problem_id=problem.id,
        problem_type=problem.problem_type,
        metrics=metrics
    )

    # Cache the result for 1 hour
    cache.set(f"performance:{problem_id}", response.json(), ex=3600)

    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
