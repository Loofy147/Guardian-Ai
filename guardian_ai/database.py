"""
Database configuration and SQLAlchemy models for the Guardian AI application.
"""
import datetime
import os
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# --- Database Configuration ---
# Use the DATABASE_URL from the environment, with a fallback to a local SQLite database.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./guardian_ai.db")

# Adjust create_engine arguments based on the database type
engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_args)
SESSION_LOCAL = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- SQLAlchemy Models ---


class Problem(Base):
    """Represents a specific problem instance being tracked."""

    __tablename__ = "problems"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), nullable=False
    )  # In a real app, this would be a foreign key to a User table
    problem_type = Column(String(50), nullable=False)
    config = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    decisions = relationship("Decision", back_populates="problem")
    historical_data = relationship("HistoricalData", back_populates="problem")


class HistoricalData(Base):
    """Represents a single data point from the problem's history."""

    __tablename__ = "historical_data"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    features = Column(JSON, nullable=False)
    outcome = Column(Float, nullable=False)

    problem = relationship("Problem", back_populates="historical_data")


class Prediction(Base):
    """Represents a prediction made by the ML model."""

    __tablename__ = "predictions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    predicted_value = Column(Float, nullable=False)
    uncertainty = Column(Float, nullable=False)
    trust_level = Column(Float, nullable=False)

    decision = relationship("Decision", uselist=False, back_populates="prediction")


class Decision(Base):
    """Represents a decision made by the LAA."""

    __tablename__ = "decisions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False)
    prediction_id = Column(
        UUID(as_uuid=True), ForeignKey("predictions.id"), nullable=True
    )
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    action = Column(String(50), nullable=False)
    actual_outcome = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    optimal_cost = Column(Float, nullable=True)

    problem = relationship("Problem", back_populates="decisions")
    prediction = relationship("Prediction", back_populates="decision")


class User(Base):
    """Represents an authenticated user."""

    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    disabled = Column(Boolean, default=False)


# --- Database Initialization ---
def create_db_and_tables():
    """
    Creates the database and all tables defined in the models.
    """
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    print("Creating database and tables...")
    create_db_and_tables()
    print("Database and tables created successfully.")
