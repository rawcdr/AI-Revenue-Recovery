from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.database import get_db
from backend.app.models.domain import Payment, Subscription

router = APIRouter()

@router.get("/metrics/revenue-at-risk")
def get_revenue_at_risk(db: Session = Depends(get_db)):
    failed_payment_sum = db.query(func.sum(Payment.amount)).filter(Payment.status == 'failed').scalar() or 0.0
    failed_payment_count = db.query(Payment).filter(Payment.status == 'failed').count()
    
    sub_risk_sum = db.query(func.sum(Subscription.mrr_value)).filter(Subscription.status.in_(['pending', 'halted'])).scalar() or 0.0
    sub_count = db.query(Subscription).filter(Subscription.status.in_(['pending', 'halted'])).count()
    
    # We document that abandoned checkouts are ignored for the recovery queue right now
    revenue_at_risk = float(failed_payment_sum + sub_risk_sum)
    
    return {
        "revenue_at_risk": revenue_at_risk,
        "currency": "INR",
        "failed_payment_count": failed_payment_count,
        "subscription_count": sub_count
    }
