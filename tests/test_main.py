import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
import os
from unittest.mock import patch

# --- Test Setup ---
# Override the database URL for testing
TEST_DATABASE_URL = "sqlite:///./test.db"
os.environ['DATABASE_URL'] = TEST_DATABASE_URL

from main import app, get_db
from guardian_ai.database import Base

# Create a new database engine for testing
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency to use the test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    # Create the tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Create a test user
    from guardian_ai.auth import create_user, UserCreate
    from guardian_ai.database import User as DBUser
    if not db.query(DBUser).filter(DBUser.username == "testuser").first():
        create_user(db, UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="testpassword"
        ))
    db.close()
    yield
    # Teardown: drop all tables
    Base.metadata.drop_all(bind=engine)

# --- Mock Hugging Face Token ---
# Set a dummy token for testing purposes
os.environ['HUGGING_FACE_TOKEN'] = "hf_test_token"

client = TestClient(app)

# --- Test Cases ---

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@patch('main.TimeSeriesPredictor')
def test_decide_endpoint(MockTimeSeriesPredictor):
    # Mock the predictor
    mock_predictor_instance = MockTimeSeriesPredictor.return_value
    mock_predictor_instance.predict.return_value = (720, 50)

    # Authenticate
    login_response = client.post("/token", data={"username": "testuser", "password": "testpassword"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    request_data = {
        "user_id": str(uuid.uuid4()),
        "problem_type": "ski_rental",
        "historical_data": [
            {"timestamp": "2023-01-01T00:00:00Z", "value": 100},
            {"timestamp": "2023-01-01T01:00:00Z", "value": 110},
        ],
        "problem_params": {"commit_cost": 500, "step_cost": 10},
        "decision_state": {"current_step": 30},
        "trust_level": 0.8,
    }

    response = client.post("/decide", json=request_data, headers=headers)

    assert response.status_code == 200
    response_json = response.json()
    assert "action" in response_json
    assert "guarantee" in response_json
    assert "problem_id" in response_json
    assert "decision_id" in response_json

@patch('main.cache')
@patch('main.TimeSeriesPredictor')
def test_log_outcome_and_performance(MockTimeSeriesPredictor, mock_cache):
    # Mock the predictor and cache
    mock_predictor_instance = MockTimeSeriesPredictor.return_value
    mock_predictor_instance.predict.return_value = (720, 50)
    mock_cache.get.return_value = None

    # Authenticate
    login_response = client.post("/token", data={"username": "testuser", "password": "testpassword"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # First, make a decision
    user_id = str(uuid.uuid4())
    request_data = {
        "user_id": user_id,
        "problem_type": "ski_rental",
        "historical_data": [{"timestamp": "2023-01-01T00:00:00Z", "value": 100}],
        "problem_params": {"commit_cost": 500, "step_cost": 10},
        "decision_state": {"current_step": 1},
        "trust_level": 0.8,
    }
    decide_response = client.post("/decide", json=request_data, headers=headers)

    decision_id = decide_response.json()["decision_id"]
    problem_id = decide_response.json()["problem_id"]

    # Now, log an outcome for that decision
    log_outcome_data = {
        "decision_id": decision_id,
        "actual_outcome": 60, # 60 hours
    }
    log_response = client.post("/log_outcome", json=log_outcome_data, headers=headers)

    assert log_response.status_code == 200
    assert log_response.json()["message"] == "Outcome logged and performance calculated successfully."

    # Finally, check the performance
    perf_response = client.get(f"/performance/{problem_id}", headers=headers)

    assert perf_response.status_code == 200
    perf_json = perf_response.json()
    assert perf_json["problem_id"] == problem_id
    assert perf_json["metrics"]["total_decisions"] == 1
    assert perf_json["metrics"]["total_cost_optimal"] is not None

def test_decide_endpoint_empty_history():
    """
    Tests that the /decide endpoint returns a 400 Bad Request error
    when the historical_data list is empty, as no prediction can be made.
    """
    # Authenticate
    login_response = client.post("/token", data={"username": "testuser", "password": "testpassword"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    request_data = {
        "user_id": str(uuid.uuid4()),
        "problem_type": "ski_rental",
        "historical_data": [],  # Empty history
        "problem_params": {"commit_cost": 500, "step_cost": 10},
        "decision_state": {"current_step": 1},
        "trust_level": 0.8,
    }

    response = client.post("/decide", json=request_data, headers=headers)

    # The request should be rejected as invalid before attempting a prediction.
    assert response.status_code == 400
    assert "no historical data" in response.json()["detail"].lower()
