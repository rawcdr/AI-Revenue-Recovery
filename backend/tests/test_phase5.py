import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.db.database import Base, get_db
from backend.app.models.domain import Customer, Payment, RecoveryCandidate, RecoveryPrediction

SQLALCHEMY_DATABASE_URL = "sqlite:///./test5.db"

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

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    c = Customer(customer_id="cus_005", customer_name="Test5", customer_segment="standard", customer_ltv=0, risk_tier="low", default_payment_method="card", created_at="2026-08-01T00:00:00")
    db.add(c)
    
    # Candidate 1: Normal RETRY (network_error) -> Simulator SUCCESS
    p1 = Payment(payment_id="pay_1", customer_id="cus_005", amount=1000, currency="INR", payment_method="card", status="failed", error_code="network_error")
    rc1 = RecoveryCandidate(candidate_id="cndt_1", entity_type="payment", entity_id="pay_1", customer_id="cus_005", candidate_type="PAYMENT_FAILURE", state="FAILED", amount=1000, retry_count=0, status="ACTIVE", detected_at="2026-09-01T10:00:00")
    pred1 = RecoveryPrediction(prediction_id="pred_1", candidate_id="cndt_1", model_version="v1", feature_version="v1", retry_probability=0.9, payment_update_probability=0.1, escalation_probability=0.0, recommended_action="RETRY", expected_recovery_value=900, explanation="test", created_at="2026-09-01T10:00:00")
    db.add_all([p1, rc1, pred1])

    # Candidate 2: Policy Block (customer_dispute)
    p2 = Payment(payment_id="pay_2", customer_id="cus_005", amount=2000, currency="INR", payment_method="card", status="failed", error_code="customer_dispute")
    rc2 = RecoveryCandidate(candidate_id="cndt_2", entity_type="payment", entity_id="pay_2", customer_id="cus_005", candidate_type="PAYMENT_FAILURE", state="FAILED", amount=2000, retry_count=0, status="ACTIVE", detected_at="2026-09-01T10:00:00")
    pred2 = RecoveryPrediction(prediction_id="pred_2", candidate_id="cndt_2", model_version="v1", feature_version="v1", retry_probability=0.8, payment_update_probability=0.1, escalation_probability=0.1, recommended_action="RETRY", expected_recovery_value=1600, explanation="test", created_at="2026-09-01T10:00:00")
    db.add_all([p2, rc2, pred2])
    
    # Candidate 3: Exceeds retry limit
    p3 = Payment(payment_id="pay_3", customer_id="cus_005", amount=3000, currency="INR", payment_method="card", status="failed", error_code="insufficient_funds")
    rc3 = RecoveryCandidate(candidate_id="cndt_3", entity_type="payment", entity_id="pay_3", customer_id="cus_005", candidate_type="PAYMENT_FAILURE", state="FAILED", amount=3000, retry_count=3, status="ACTIVE", detected_at="2026-09-01T10:00:00")
    pred3 = RecoveryPrediction(prediction_id="pred_3", candidate_id="cndt_3", model_version="v1", feature_version="v1", retry_probability=0.9, payment_update_probability=0.1, escalation_probability=0.0, recommended_action="RETRY", expected_recovery_value=2700, explanation="test", created_at="2026-09-01T10:00:00")
    db.add_all([p3, rc3, pred3])
    
    # Candidate 4: Missing prediction (handled safely)
    p4 = Payment(payment_id="pay_4", customer_id="cus_005", amount=4000, currency="INR", payment_method="card", status="failed", error_code="insufficient_funds")
    rc4 = RecoveryCandidate(candidate_id="cndt_4", entity_type="payment", entity_id="pay_4", customer_id="cus_005", candidate_type="PAYMENT_FAILURE", state="FAILED", amount=4000, retry_count=0, status="ACTIVE", detected_at="2026-09-01T10:00:00")
    db.add_all([p4, rc4])

    db.commit()
    db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test5.db"):
        os.remove("./test5.db")


def test_successful_execution_and_idempotency():
    # Execute cndt_1 (Network error + RETRY -> SUCCESS)
    resp = client.post("/recovery/cndt_1/execute")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCEEDED"
    assert data["result"] == "SUCCESS"
    
    data["action_id"]
    
    # Idempotency test: duplicate execution must return 409 Conflict
    resp2 = client.post("/recovery/cndt_1/execute")
    assert resp2.status_code == 409
    data2 = resp2.json()
    assert "error" in data2
    
    # Candidate state should be updated
    db = TestingSessionLocal()
    rc = db.query(RecoveryCandidate).filter_by(candidate_id="cndt_1").first()
    assert rc.status == "RESOLVED"
    assert rc.state == "RECOVERED"
    assert rc.retry_count == 1
    db.close()


def test_policy_blocks_dispute():
    # Even if ML says RETRY, policy should block because it's a dispute
    resp = client.post("/recovery/cndt_2/execute")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "BLOCKED"


def test_policy_blocks_max_retries():
    # retry_count is 3, attempting again makes it attempt_number 4, which > 3
    resp = client.post("/recovery/cndt_3/execute")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "BLOCKED"


def test_missing_prediction_handled_safely():
    # No prediction exists, so it should generate one securely on the fly and execute
    resp = client.post("/recovery/cndt_4/execute")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ["SUCCEEDED", "FAILED", "BLOCKED"]


def test_recovery_metrics():
    # Execute some
    client.post("/recovery/cndt_1/execute") # Succeeded (1000)
    client.post("/recovery/cndt_2/execute") # Blocked
    
    resp = client.get("/metrics/recovery")
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["total_recovery_actions"] >= 2
    assert data["revenue_recovered"] == 1000.0
    assert "RETRY" in data["recovery_amount_by_action_type"]
    assert data["recovery_amount_by_action_type"]["RETRY"] == 1000.0


def test_legitimate_second_retry():
    # Execute attempt 1
    resp = client.post("/recovery/cndt_1/execute")
    assert resp.status_code == 200
    
    # We must mock that it failed so it allows a second retry.
    db = TestingSessionLocal()
    rc = db.query(RecoveryCandidate).filter_by(candidate_id="cndt_1").first()
    rc.status = "ACTIVE"
    rc.state = "FAILED"
    db.commit()
    db.close()
    
    # Execute attempt 2
    resp2 = client.post("/recovery/cndt_1/execute")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["status"] in ["SUCCEEDED", "FAILED", "BLOCKED"]
    
    # Verify idempotency key was different and attempt_number was 2
    from backend.app.models.domain import RecoveryAction
    db = TestingSessionLocal()
    action = db.query(RecoveryAction).filter_by(action_id=data["action_id"]).first()
    assert action.attempt_number == 2
    assert action.idempotency_key == "cndt_1_RETRY_2"
    db.close()


def test_not_recovered_outcome_and_simulator_determinism():
    # cndt_4 has insufficient_funds and retry_count=0
    # simulator uses hash(candidate_id) % 100 for insufficient_funds.
    resp = client.post("/recovery/cndt_4/execute")
    assert resp.status_code == 200
    
    from backend.app.models.domain import RecoveryOutcome
    db = TestingSessionLocal()
    outcome = db.query(RecoveryOutcome).filter_by(candidate_id="cndt_4").first()
    
    assert outcome is not None
    assert outcome.outcome in ["RECOVERED", "NOT_RECOVERED"]
    
    if outcome.outcome == "NOT_RECOVERED":
        assert outcome.recovered_amount == 0.0
    db.close()


def test_no_revenue_double_counting():
    db = TestingSessionLocal()
    from backend.app.models.domain import RecoveryAction, RecoveryOutcome
    import uuid
    # Create two successful actions for same candidate manually
    a1 = RecoveryAction(action_id=f"act_{uuid.uuid4().hex[:16]}", candidate_id="cndt_double", action_type="RETRY", status="SUCCEEDED", idempotency_key="double_1", attempt_number=1, created_at="2026-01-01")
    o1 = RecoveryOutcome(outcome_id=f"out_{uuid.uuid4().hex[:16]}", action_id=a1.action_id, candidate_id="cndt_double", outcome="RECOVERED", recovered_amount=1000.0, created_at="2026-01-01")
    
    a2 = RecoveryAction(action_id=f"act_{uuid.uuid4().hex[:16]}", candidate_id="cndt_double", action_type="RETRY", status="SUCCEEDED", idempotency_key="double_2", attempt_number=2, created_at="2026-01-01")
    o2 = RecoveryOutcome(outcome_id=f"out_{uuid.uuid4().hex[:16]}", action_id=a2.action_id, candidate_id="cndt_double", outcome="RECOVERED", recovered_amount=1000.0, created_at="2026-01-01")
    
    db.add_all([a1, o1, a2, o2])
    db.commit()
    db.close()
    
    resp = client.get("/metrics/recovery")
    data = resp.json()
    assert data["revenue_recovered"] == 1000.0
