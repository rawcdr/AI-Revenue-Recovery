from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.database import get_db
from backend.app.models.domain import RecoveryCandidate

router = APIRouter()

@router.get("/metrics/revenue-at-risk")
def get_revenue_at_risk(db: Session = Depends(get_db)):
    active_candidates = db.query(RecoveryCandidate).filter(RecoveryCandidate.status == "ACTIVE").all()
    revenue_at_risk = sum(c.amount for c in active_candidates)
    
    failed_payment_count = sum(1 for c in active_candidates if c.entity_type == "payment")
    subscription_count = sum(1 for c in active_candidates if c.entity_type == "subscription")
    
    return {
        "revenue_at_risk": revenue_at_risk,
        "currency": "INR",
        "failed_payment_count": failed_payment_count,
        "subscription_count": subscription_count
    }
