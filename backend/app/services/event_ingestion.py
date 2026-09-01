import json
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.schemas.schemas import NormalizedEvent
from backend.app.models.domain import Event, Payment, Subscription

def process_event(db: Session, event: NormalizedEvent):
    # Idempotency check
    existing_event = db.query(Event).filter(Event.event_id == event.event_id).first()
    if existing_event:
        return {"status": "duplicate", "event_id": event.event_id}
        
    # Persist Event
    db_event = Event(
        event_id=event.event_id,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        customer_id=event.customer_id,
        event_type=event.event_type,
        amount=event.amount,
        currency=event.currency,
        timestamp=event.timestamp,
        metadata_=json.dumps(event.metadata),
        received_at=datetime.now().isoformat()
    )
    db.add(db_event)
    
    # Update Entity State deterministically
    if event.entity_type == "payment":
        payment = db.query(Payment).filter(Payment.payment_id == event.entity_id).first()
        if payment:
            if event.event_type == "payment.failed":
                payment.status = "failed"
                payment.failed_at = event.timestamp
            elif event.event_type == "payment.captured":
                payment.status = "captured"
    elif event.entity_type == "subscription":
        subscription = db.query(Subscription).filter(Subscription.subscription_id == event.entity_id).first()
        if subscription:
            if event.event_type == "subscription.pending":
                subscription.status = "pending"
                subscription.pending_since = event.timestamp
            elif event.event_type == "subscription.halted":
                subscription.status = "halted"
                subscription.halted_at = event.timestamp
                
    db.commit()
    return {"status": "processed", "event_id": event.event_id}
