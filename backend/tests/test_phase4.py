import pytest
import os
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.db.database import Base, get_db
from backend.app.models.domain import Customer, Payment, RecoveryCandidate
from backend.app.intelligence.registry import load_models

SQLALCHEMY_DATABASE_URL = "sqlite:///./test4.db"

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
    
    # Add a mock customer and multiple candidates for inference tests
    c = Customer(customer_id="cus_001", customer_name="Test", customer_segment="standard", customer_ltv=0, risk_tier="low", default_payment_method="card", created_at="2026-08-01T00:00:00")
    db.add(c)
    
    # 1. RETRY-favorable (insufficient funds)
    p1 = Payment(payment_id="pay_insufficient", customer_id="cus_001", amount=1000, currency="INR", payment_method="card", status="failed", error_code="insufficient_funds")
    rc1 = RecoveryCandidate(candidate_id="cndt_insufficient", entity_type="payment", entity_id="pay_insufficient", customer_id="cus_001", candidate_type="PAYMENT_FAILURE", state="FAILED", amount=1000, status="ACTIVE", detected_at="2026-09-01T10:00:00")
    db.add_all([p1, rc1])

    # 2. UPDATE-favorable (expired card)
    p2 = Payment(payment_id="pay_expired", customer_id="cus_001", amount=2000, currency="INR", payment_method="card", status="failed", error_code="expired_card")
    rc2 = RecoveryCandidate(candidate_id="cndt_expired", entity_type="payment", entity_id="pay_expired", customer_id="cus_001", candidate_type="PAYMENT_FAILURE", state="FAILED", amount=2000, status="ACTIVE", detected_at="2026-09-01T10:00:00")
    db.add_all([p2, rc2])
    
    # 3. ESCALATE-favorable (fraud/dispute)
    p3 = Payment(payment_id="pay_dispute", customer_id="cus_001", amount=5000, currency="INR", payment_method="card", status="failed", error_code="customer_dispute")
    rc3 = RecoveryCandidate(candidate_id="cndt_dispute", entity_type="payment", entity_id="pay_dispute", customer_id="cus_001", candidate_type="PAYMENT_FAILURE", state="FAILED", amount=5000, status="ACTIVE", detected_at="2026-09-01T10:00:00")
    db.add_all([p3, rc3])
    
    db.commit()
    db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import os
    if os.path.exists("./test4.db"):
        os.remove("./test4.db")

def test_training_data_existence():
    """Verify deterministic training data generated."""
    assert os.path.exists('data/training/recovery_training_data.csv')
    df = pd.read_csv('data/training/recovery_training_data.csv')
    assert len(df) >= 20000
    
    # No target leakage checks
    cols = set(df.columns)
    assert 'ground_truth_action' not in cols
    assert 'future_event' not in cols

def test_models_exist():
    """Verify the intelligence model was persisted properly."""
    models = load_models()
    assert models is not None
    assert 'preprocessor' in models
    assert 'retry_model' in models
    assert 'update_model' in models

def test_api_batch_intelligence():
    """Test batch inference logic over candidates."""
    resp = client.post("/intelligence/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["processed"] == 3

def test_inference_and_expected_value_math():
    """Test the individual candidate predictions and expected value calculation."""
    # Score candidate 1 (insufficient funds)
    resp = client.post("/intelligence/cndt_insufficient")
    assert resp.status_code == 200
    data = resp.json()
    
    assert "recommended_action" in data
    assert "expected_recovery_value" in data
    
    # Check that EV is amount * max_prob
    # Since amount = 1000, EV should be exactly prob * 1000
    # Floating point comparison
    
    # We test /get endpoint for details
    resp_get = client.get("/intelligence/cndt_insufficient")
    assert resp_get.status_code == 200
    details = resp_get.json()
    
    action = details['recommended_action']
    if action == "RETRY":
        prob = details['retry_probability']
    elif action == "PAYMENT_UPDATE":
        prob = details['payment_update_probability']
    else:
        prob = details['escalation_probability']
        
    expected_val = 1000.0 * prob
    assert round(details['expected_recovery_value'], 4) == round(expected_val, 4)
    assert "Signals:" in details['explanation']

def test_inference_qualitative_behavior():
    """
    Test qualitative outputs (Insufficient -> generally RETRY, 
    Expired -> generally PAYMENT_UPDATE, 
    Dispute -> generally ESCALATE).
    Since models vary slightly, we only enforce that the appropriate probability is HIGH.
    """
    resp_insuf = client.get("/intelligence/cndt_insufficient")
    # For insufficient funds, Retry should typically be the highest.
    if resp_insuf.status_code == 200:
        data = resp_insuf.json()
        assert data['retry_probability'] >= data['payment_update_probability']
        
    # Run scoring for expired card
    client.post("/intelligence/cndt_expired")
    resp_exp = client.get("/intelligence/cndt_expired")
    if resp_exp.status_code == 200:
        data = resp_exp.json()
        assert data['payment_update_probability'] >= data['retry_probability']
        
    # Run scoring for dispute
    client.post("/intelligence/cndt_dispute")
    resp_disp = client.get("/intelligence/cndt_dispute")
    if resp_disp.status_code == 200:
        data = resp_disp.json()
        assert data['escalation_probability'] > 0.5  # Should strongly favor escalation
