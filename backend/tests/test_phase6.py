import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.db.database import Base, get_db
from backend.app.models.domain import (
    Customer, Payment, RecoveryCandidate, RecoveryPrediction, 
    RecoveryAction, RecoveryOutcome, RecoveryFeedback, ModelRegistry
)

SQLALCHEMY_DATABASE_URL = "sqlite:///./test6.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Insert Mock Models
    m1 = ModelRegistry(version_id="v1", model_version="recovery-v1", model_type="sklearn", feature_version="v1", status="VALIDATED", training_timestamp="2026-09-01T00:00:00")
    m2 = ModelRegistry(version_id="v2", model_version="recovery-v2", model_type="sklearn", feature_version="v1", status="ACTIVE", training_timestamp="2026-09-02T00:00:00")
    db.add_all([m1, m2])
    
    # Insert Mock Feedback Loop 
    fb1 = RecoveryFeedback(
        feedback_id="fb_1", candidate_id="cndt_1", prediction_id="pred_1", action_id="act_1",
        model_version="recovery-v2", feature_version="v1", recommended_action="RETRY",
        recommended_probability=0.9, expected_recovery_value=900.0,
        actual_action="RETRY", action_status="SUCCEEDED", actual_outcome="RECOVERED",
        recovered_amount=1000.0, created_at="2026-09-03T10:00:00"
    )
    # Duplicate feedback simulation (should be deduplicated by candidate in revenue check)
    fb2 = RecoveryFeedback(
        feedback_id="fb_2", candidate_id="cndt_1", prediction_id="pred_2", action_id="act_2",
        model_version="recovery-v2", feature_version="v1", recommended_action="RETRY",
        recommended_probability=0.9, expected_recovery_value=900.0,
        actual_action="RETRY", action_status="SUCCEEDED", actual_outcome="RECOVERED",
        recovered_amount=1000.0, created_at="2026-09-03T10:05:00"
    )
    # Failed action feedback
    fb3 = RecoveryFeedback(
        feedback_id="fb_3", candidate_id="cndt_2", prediction_id="pred_3", action_id="act_3",
        model_version="recovery-v2", feature_version="v1", recommended_action="PAYMENT_UPDATE",
        recommended_probability=0.1, expected_recovery_value=100.0,
        actual_action="PAYMENT_UPDATE", action_status="FAILED", actual_outcome="NOT_RECOVERED",
        recovered_amount=0.0, created_at="2026-09-03T10:10:00"
    )
    db.add_all([fb1, fb2, fb3])
    db.commit()
    db.close()
    
    yield
    
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test6.db"):
        try:
            os.remove("./test6.db")
        except:
            pass

def test_metrics_feedback_deduplication_and_calibration():
    resp = client.get("/metrics/feedback")
    assert resp.status_code == 200
    data = resp.json()
    
    # 1. Action Performance
    assert "RETRY" in data["action_performance"]
    # Total RETRY count is 2, successful executions = 2, recovered count = 2
    assert data["action_performance"]["RETRY"]["count"] == 2
    assert data["action_performance"]["RETRY"]["successful_executions"] == 2
    assert data["action_performance"]["RETRY"]["recovered_count"] == 2
    
    # 2. Revenue deduplication
    rev = data["revenue_metrics"]
    # fb1 and fb2 are the same candidate_id="cndt_1". Revenue recovered should be exactly 1000.0, NOT 2000.0
    assert rev["realized_recovery_value"] == 1000.0
    
    # 3. Calibration
    # fb1 and fb2 prob = 0.9 (bucket 0.8-1.0)
    # fb3 prob = 0.1 (bucket 0.0-0.2)
    assert "0.8-1.0" in data["calibration"]
    assert data["calibration"]["0.8-1.0"]["prediction_count"] == 2
    assert data["calibration"]["0.8-1.0"]["actual_recovery_rate"] == 1.0
    
    assert "0.0-0.2" in data["calibration"]
    assert data["calibration"]["0.0-0.2"]["prediction_count"] == 1
    assert data["calibration"]["0.0-0.2"]["actual_recovery_rate"] == 0.0

def test_model_registry_list():
    resp = client.get("/intelligence/models")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    versions = [d["model_version"] for d in data]
    assert "recovery-v1" in versions
    assert "recovery-v2" in versions

def test_model_registry_get_specific():
    resp = client.get("/intelligence/models/recovery-v2")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"

def test_model_promotion_script_logic():
    # We will invoke the registry service directly to test promotion logic
    from backend.app.services.registry import promote_model, get_active_model
    db = TestingSessionLocal()
    
    active = get_active_model(db)
    assert active.model_version == "recovery-v2"
    
    # Promote v1 which is VALIDATED
    promote_model(db, "recovery-v1")
    
    active_now = get_active_model(db)
    assert active_now.model_version == "recovery-v1"
    
    # Old active should be retired
    old_active = db.query(ModelRegistry).filter_by(model_version="recovery-v2").first()
    assert old_active.status == "RETIRED"
    
    # Cannot promote a RETIRED model (raises ValueError)
    with pytest.raises(ValueError) as exc:
        promote_model(db, "recovery-v2")
    assert "Must be VALIDATED" in str(exc.value)
    
    db.close()

def test_drift_and_retraining():
    resp = client.get("/intelligence/drift")
    assert resp.status_code == 200
    data = resp.json()
    
    # We only seeded 3 feedbacks, which is < 50
    assert data["drift_status"] == "NO_DRIFT"
    assert data["retraining_recommendation"] == "NO_RETRAINING_REQUIRED"
    assert "Insufficient feedback data" in data["reason"]

def test_leakage_protection_by_schema():
    # Verify that RecoveryPrediction schema does NOT contain actual_outcome or recovered_amount
    from backend.app.models.domain import RecoveryPrediction
    columns = [c.name for c in RecoveryPrediction.__table__.columns]
    
    assert "actual_outcome" not in columns
    assert "recovered_amount" not in columns
    assert "status" not in columns # status of the outcome, not candidate
    assert "ground_truth_action" not in columns
