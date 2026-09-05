import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.main import app
from backend.app.db.database import Base, get_db
from backend.app.models.domain import Payment, Subscription, Customer, RecoveryCandidate
from backend.app.services.detection import run_detection, get_priority_score

SQLALCHEMY_DATABASE_URL = "sqlite:///./test3.db"

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
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    c = Customer(customer_id="cus_001", customer_name="Test", customer_segment="standard", customer_ltv=0, risk_tier="low", default_payment_method="card", created_at="2026-08-01T00:00:00")
    db.add(c)
    
    p = Payment(payment_id="pay_001", customer_id="cus_001", amount=1000, currency="INR", payment_method="card", status="failed", created_at="2026-08-01T00:00:00", retry_count=0, error_code="insufficient_funds")
    db.add(p)
    
    s = Subscription(subscription_id="sub_001", customer_id="cus_001", plan_id="plan_basic", mrr_value=500, currency="INR", status="pending", auth_attempts=0, paid_count=1, created_at="2026-08-01T00:00:00")
    db.add(s)
    
    db.commit()
    db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield
    
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import os
    if os.path.exists("./test3.db"):
        os.remove("./test3.db")

def test_detection_creates_candidates():
    db = TestingSessionLocal()
    stats = run_detection(db)
    assert stats["new_candidates"] == 2
    assert stats["active_candidates"] == 2
    
    cands = db.query(RecoveryCandidate).all()
    assert len(cands) == 2
    
    p_cand = [c for c in cands if c.entity_id == "pay_001"][0]
    assert p_cand.state == "FAILED"
    assert p_cand.priority_score == 1000.0  # 1000 * 1 * 1 * 1
    
    db.close()

def test_detection_deduplication():
    db = TestingSessionLocal()
    stats1 = run_detection(db)
    assert stats1["new_candidates"] == 2
    
    # Run again without changes
    stats2 = run_detection(db)
    assert stats2["new_candidates"] == 0
    assert stats2["updated_candidates"] == 0
    
    cands = db.query(RecoveryCandidate).all()
    assert len(cands) == 2
    db.close()

def test_state_transition_updates_candidate():
    db = TestingSessionLocal()
    run_detection(db)
    
    sub = db.query(Subscription).filter_by(subscription_id="sub_001").first()
    sub.status = "halted"
    db.commit()
    
    stats = run_detection(db)
    assert stats["updated_candidates"] == 1
    
    cand = db.query(RecoveryCandidate).filter_by(entity_id="sub_001").first()
    assert cand.state == "HALTED"
    assert cand.priority_score == 750.0  # 500 * 1 * 1.5 * 1
    db.close()

def test_captured_payment_resolves_candidate():
    db = TestingSessionLocal()
    run_detection(db)
    
    p = db.query(Payment).filter_by(payment_id="pay_001").first()
    p.status = "captured"
    db.commit()
    
    stats = run_detection(db)
    assert stats["resolved_candidates"] == 1
    
    cand = db.query(RecoveryCandidate).filter_by(entity_id="pay_001").first()
    assert cand.status == "RESOLVED"
    db.close()

def test_priority_score_logic():
    assert round(get_priority_score(100, "high_value", 1.0, 0), 2) == 150.0
    assert round(get_priority_score(100, "new", 1.0, 0), 2) == 80.0
    assert round(get_priority_score(100, "standard", 1.5, 0), 2) == 150.0
    assert round(get_priority_score(100, "standard", 1.0, 1), 2) == 110.0
    assert round(get_priority_score(100, "standard", 1.0, 2), 2) == 120.0
    assert round(get_priority_score(100, "standard", 1.0, 3), 2) == 50.0

def test_api_detection_run():
    resp = client.post("/detection/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_candidates"] == 2
    
def test_api_metrics():
    client.post("/detection/run")
    resp = client.get("/metrics/revenue-at-risk")
    assert resp.status_code == 200
    data = resp.json()
    assert data["revenue_at_risk"] == 1500.0  # 1000 + 500
