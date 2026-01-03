"""
SQLAlchemy database models for ML service.
"""
from sqlalchemy import Column, String, Float, DateTime, Integer, JSON, Text
from sqlalchemy.sql import func
from src.database.connection import Base


class ChargerMetrics(Base):
    """Charger metrics storage for training data."""
    __tablename__ = "charger_metrics"
    
    id = Column(String, primary_key=True)
    charger_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    
    # Metrics
    connector_status = Column(String)
    energy_delivered = Column(Float)
    power = Column(Float)
    temperature = Column(Float)
    error_codes = Column(JSON)
    uptime_hours = Column(Float)
    total_sessions = Column(Integer)
    
    # Metadata
    raw_data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())


class Prediction(Base):
    """Stored predictions."""
    __tablename__ = "predictions"
    
    id = Column(String, primary_key=True)
    charger_id = Column(String, nullable=False, index=True)
    model_type = Column(String, nullable=False)  # failure_predictor, maintenance_scheduler
    model_version = Column(String, nullable=False)
    
    # Prediction results
    prediction_data = Column(JSON, nullable=False)
    confidence = Column(Float)
    
    # Timestamps
    predicted_at = Column(DateTime, server_default=func.now(), index=True)
    created_at = Column(DateTime, server_default=func.now())


class ModelMetadata(Base):
    """Model metadata and versioning."""
    __tablename__ = "model_metadata"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    version = Column(String, nullable=False)
    type = Column(String, nullable=False)  # classification, regression
    
    # Model info
    accuracy = Column(Float)
    path = Column(String)
    metadata = Column(JSON)
    
    # Status
    status = Column(String, default="UNLOADED")  # LOADED, UNLOADED, ERROR
    loaded_at = Column(DateTime)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

