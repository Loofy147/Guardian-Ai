import cProfile
import pstats
from fastapi.testclient import TestClient
from main import app, get_db
from guardian_ai.database import create_db_and_tables, User as DBUser
from guardian_ai.auth import create_user, UserCreate

# --- Test Setup ---
# Create the tables and a test user
create_db_and_tables()
db = next(get_db())
if not db.query(DBUser).filter(DBUser.username == "testuser").first():
    create_user(
        db,
        UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="testpassword",
        ),
    )
db.close()


client = TestClient(app)


def profile_decide_endpoint():
    """Profiles the /decide endpoint."""
    login_response = client.post(
        "/token", data={"username": "testuser", "password": "testpassword"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    request_data = {
        "user_id": "e9a8b6f0-3c1d-4e8a-9f2a-8c7d6e5a4b3b",
        "problem_type": "ski_rental",
        "historical_data": [
            {"timestamp": "2023-01-01T00:00:00Z", "value": 100},
            {"timestamp": "2023-01-01T01:00:00Z", "value": 110},
        ],
        "problem_params": {"commit_cost": 500, "step_cost": 10},
        "decision_state": {"current_step": 30},
        "trust_level": 0.8,
    }

    with cProfile.Profile() as pr:
        for _ in range(10):
            client.post("/decide", json=request_data, headers=headers)

    stats = pstats.Stats(pr)
    stats.sort_stats(pstats.SortKey.TIME)
    stats.print_stats(10)

if __name__ == "__main__":
    profile_decide_endpoint()
