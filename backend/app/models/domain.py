from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime
from backend.app.db.database import Base

class Customer(Base):
    __tablename__ = "customers"
    
    customer_id = Column(String, primary_key=True, index=True)
    customer_name = Column(String)
    customer_segment = Column(String)
    customer_ltv = Column(Float)
    risk_tier = Column(String)
    default_payment_method = Column(String)
    created_at = Column(String)

class Payment(Base):
    __tablename__ = "payments"
    
    payment_id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True)
    amount = Column(Float)
    currency = Column(String)
    payment_method = Column(String)
    status = Column(String)
    created_at = Column(String)
    failed_at = Column(String, nullable=True)
    retry_count = Column(Integer)
    error_code = Column(String, nullable=True)
    error_source = Column(String, nullable=True)
    recoverable = Column(String, nullable=True)
    ground_truth_root_cause = Column(String, nullable=True)
    ground_truth_action = Column(String, nullable=True)

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    subscription_id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True)
    plan_id = Column(String)
    mrr_value = Column(Float)
    currency = Column(String)
    status = Column(String)
    auth_attempts = Column(Integer)
    paid_count = Column(Integer)
    created_at = Column(String)
    pending_since = Column(String, nullable=True)
    halted_at = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)
    recoverable = Column(String, nullable=True)
    ground_truth_action = Column(String, nullable=True)

class Event(Base):
    __tablename__ = "events"
    
    event_id = Column(String, primary_key=True, index=True)
    entity_type = Column(String)
    entity_id = Column(String, index=True)
    customer_id = Column(String, index=True)
    event_type = Column(String)
    amount = Column(Float)
    currency = Column(String)
    timestamp = Column(String)
    metadata_ = Column("metadata", String)  # Using metadata_ since metadata is reserved in SQLAlchemy
    received_at = Column(String)

class RecoveryCandidate(Base):
    __tablename__ = "recovery_candidates"
    
    candidate_id = Column(String, primary_key=True, index=True)
    entity_type = Column(String)
    entity_id = Column(String, index=True, unique=True)
    customer_id = Column(String, index=True)
    candidate_type = Column(String)
    state = Column(String)
    amount = Column(Float)
    currency = Column(String)
    retry_count = Column(Integer)
    priority_score = Column(Float)
    severity = Column(String)
    detection_reason = Column(String)
    detected_at = Column(String)
    status = Column(String, index=True)

class RecoveryPrediction(Base):
    __tablename__ = "recovery_predictions"
    
    prediction_id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, index=True)
    model_version = Column(String)
    feature_version = Column(String)
    
    retry_probability = Column(Float)
    payment_update_probability = Column(Float)
    escalation_probability = Column(Float)
    
    recommended_action = Column(String)
    expected_recovery_value = Column(Float)
    explanation = Column(String)
    
    created_at = Column(String)
