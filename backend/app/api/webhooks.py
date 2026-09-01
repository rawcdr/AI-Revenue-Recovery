from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.schemas.schemas import WebhookPayload
from backend.app.services.event_normalization import normalize_razorpay_event
from backend.app.services.event_ingestion import process_event

router = APIRouter()

SUPPORTED_EVENTS = {
    "payment.created", "payment.failed", "payment.authorized", "payment.captured",
    "subscription.created", "subscription.pending", "subscription.halted",
    "checkout.created", "checkout.abandoned", "checkout.completed"
}

@router.post("/webhooks/razorpay")
def razorpay_webhook(payload: WebhookPayload, db: Session = Depends(get_db)):
    if payload.event not in SUPPORTED_EVENTS:
        raise HTTPException(status_code=400, detail="Event type not supported")
        
    normalized = normalize_razorpay_event(payload)
    result = process_event(db, normalized)
    return result
