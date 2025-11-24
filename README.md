# Guardian AI

Guardian AI is a decision support platform for online optimization problems. It combines Machine Learning (ML) predictions with Learning-Augmented Algorithms (LAAs) to provide decisions with worst-case performance guarantees.

## Architecture

The application is composed of a React frontend and a Python backend. The backend is built with FastAPI and uses a PostgreSQL database for data storage, Redis for caching, and Celery for asynchronous task processing. The frontend is a single-page application built with React.

The application is containerized using Docker and orchestrated with Docker Compose.

## Setup

### Prerequisites

- Docker
- Docker Compose

### Running the Application

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/guardian-ai.git
   cd guardian-ai
   ```

2. **Set up environment variables:**

   Create a `.env` file in the root of the project and add the following environment variables:

   ```
   HUGGING_FACE_TOKEN=your_hugging_face_token
   ```

3. **Build and run the application:**

   ```bash
   docker-compose up --build
   ```

   The frontend will be available at `http://localhost:3000` and the backend at `http://localhost:8000`.

## Usage

The API documentation is available at `http://localhost:8000/docs` when the application is running.

### Example: Making a Decision

To make a decision, send a POST request to the `/decide` endpoint with the following payload:

```json
{
  "user_id": "your_user_id",
  "problem_type": "ski_rental",
  "historical_data": [
    {"timestamp": "2023-01-01T00:00:00Z", "value": 100},
    {"timestamp": "2023-01-01T01:00:00Z", "value": 110}
  ],
  "problem_params": {
    "commit_cost": 500,
    "step_cost": 10
  },
  "decision_state": {
    "current_step": 30
  },
  "trust_level": 0.8
}
```
