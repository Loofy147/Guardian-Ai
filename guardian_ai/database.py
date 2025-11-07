import uuid
from sqlalchemy import create_engine, Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
import datetime

# --- Database Configuration ---
# For simplicity, we'll use a local SQLite database.
# To switch to PostgreSQL, change the DATABASE_URL.
# e.g., "postgresql://user:password@host:port/dbname"
DATABASE_URL = "sqlite:///./guardian_ai.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLAlchemy Models ---

class Problem(Base):
    __tablename__ = "problems"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False) # In a real app, this would be a foreign key to a User table
    problem_type = Column(String(50), nullable=False)
    config = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    decisions = relationship("Decision", back_populates="problem")
    historical_data = relationship("HistoricalData", back_populates="problem")

class HistoricalData(Base):
    __tablename__ = "historical_data"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    features = Column(JSON, nullable=False)
    outcome = Column(Float, nullable=False)

    problem = relationship("Problem", back_populates="historical_data")

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    predicted_value = Column(Float, nullable=False)
    uncertainty = Column(Float, nullable=False)
    trust_level = Column(Float, nullable=False)

    decision = relationship("Decision", uselist=False, back_populates="prediction")

class Decision(Base):
    __tablename__ = "decisions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False)
    prediction_id = Column(UUID(as_uuid=True), ForeignKey("predictions.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    action = Column(String(50), nullable=False)
    actual_outcome = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    optimal_cost = Column(Float, nullable=True)

    problem = relationship("Problem", back_populates="decisions")
    prediction = relationship("Prediction", back_populates="decision")


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
