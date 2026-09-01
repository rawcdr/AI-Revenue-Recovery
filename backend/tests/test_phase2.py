import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.main import app
from backend.app.db.database import Base, get_db
from backend.app.models.domain import Event, Payment, Subscription, Customer


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

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
    # Add dummy customer for referential logic if needed
    c = Customer(customer_id="cus_001", customer_name="Test", customer_segment="standard", customer_ltv=0, risk_tier="low", default_payment_method="card", created_at="2026-08-01T00:00:00")
    db.add(c)
    
    # Add dummy payment for state updates
    p = Payment(payment_id="pay_001", customer_id="cus_001", amount=4999, currency="INR", payment_method="card", status="captured", created_at="2026-08-01T00:00:00")
    db.add(p)
    
    # Add dummy subscription
    s = Subscription(subscription_id="sub_001", customer_id="cus_001", plan_id="plan_basic", mrr_value=499, currency="INR", status="active", auth_attempts=0, paid_count=1, created_at="2026-08-01T00:00:00")
    db.add(s)
    
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import os
    if os.path.exists("./test.db"):
        os.remove("./test.db")

def test_webhook_invalid_event():
    response = client.post("/webhooks/razorpay", json={
        "event": "invalid.event",
        "payload": {}
    })
    assert response.status_code == 400

def test_webhook_valid_and_normalization_persistence():
    payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_001",
                    "amount": 499900,
                    "currency": "INR",
                    "customer_id": "cus_001"
                }
            }
        }
    }
    # 1. Persistence
    response = client.post("/webhooks/razorpay", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    event_id = data["event_id"]
    
    # Check DB
    db = TestingSessionLocal()
    db_event = db.query(Event).filter(Event.event_id == event_id).first()
    assert db_event is not None
    assert db_event.entity_type == "payment"
    assert db_event.amount == 4999.0
    
    # Check Payment state
    payment = db.query(Payment).filter(Payment.payment_id == "pay_001").first()
    assert payment.status == "failed"
    assert payment.failed_at is not None
    db.close()

def test_webhook_idempotency():
    payload = {
        "id": "evt_test_123",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_002",
                    "amount": 10000,
                    "currency": "INR"
                }
            }
        }
    }
    r1 = client.post("/webhooks/razorpay", json=payload)
    assert r1.status_code == 200
    assert r1.json()["status"] == "processed"
    
    r2 = client.post("/webhooks/razorpay", json=payload)
    assert r2.status_code == 200
    assert r2.json()["status"] == "duplicate"
    
    db = TestingSessionLocal()
    count = db.query(Event).filter(Event.event_id == "evt_test_123").count()
    assert count == 1
    db.close()

def test_subscription_state_update():
    payload = {
        "event": "subscription.pending",
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_001",
                    "mrr_value": 49900,
                    "currency": "INR"
                }
            }
        }
    }
    client.post("/webhooks/razorpay", json=payload)
    db = TestingSessionLocal()
    sub = db.query(Subscription).filter(Subscription.subscription_id == "sub_001").first()
    assert sub.status == "pending"
    assert sub.pending_since is not None
    db.close()

def test_recovery_queue_and_metrics():
    # Make payment failed and sub pending
    client.post("/webhooks/razorpay", json={
        "event": "payment.failed",
        "payload": {"payment": {"entity": {"id": "pay_001", "amount": 499900}}}
    })
    client.post("/webhooks/razorpay", json={
        "event": "subscription.pending",
        "payload": {"subscription": {"entity": {"id": "sub_001", "mrr_value": 49900}}}
    })
    
    q_resp = client.get("/recovery/queue")
    assert q_resp.status_code == 200
    q = q_resp.json()
    assert len(q) == 2
    # standard factor is 1.0, so priority is amount
    # pay_001 -> 4999 * 1 = 4999
    # sub_001 -> 499 * 1 = 499
    assert q[0]["amount"] == 4999
    
    m_resp = client.get("/metrics/revenue-at-risk")
    assert m_resp.status_code == 200
    m = m_resp.json()
    assert m["failed_payment_count"] == 1
    assert m["subscription_count"] == 1
    assert m["revenue_at_risk"] == 4999 + 499
