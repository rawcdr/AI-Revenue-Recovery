import uuid
from datetime import datetime
from backend.app.schemas.schemas import WebhookPayload, NormalizedEvent

def normalize_razorpay_event(payload: WebhookPayload) -> NormalizedEvent:
    event_type = payload.event
    entity_type = event_type.split('.')[0]
    
    # Razorpay payload usually has payload[entity_type]["entity"]
    entity_data = payload.payload.get(entity_type, {}).get("entity", {})
    
    # Top-level event ID or fallback
    event_id = getattr(payload, "id", None) or payload.payload.get("id") or f"evt_{uuid.uuid4().hex[:16]}"
    
    entity_id = entity_data.get("id", "")
    customer_id = entity_data.get("customer_id", "")
    
    # Amounts in razorpay webhooks are typically in paise (subunits)
    raw_amount = entity_data.get("amount", 0)
    # But for subscription it might be mrr_value? Let's check keys
    if "mrr_value" in entity_data:
        raw_amount = entity_data.get("mrr_value", 0)
        
    amount = float(raw_amount) / 100.0 if raw_amount > 10000 else float(raw_amount)
    # Actually, the prompt says amount: 499900 -> 4999. So divide by 100.
    amount = float(raw_amount) / 100.0 if raw_amount else 0.0
    
    currency = entity_data.get("currency", "INR")
    
    # Try to extract a timestamp
    timestamp = entity_data.get("created_at")
    if not timestamp:
        timestamp = datetime.now().isoformat()
        
    # Any extra fields to metadata
    metadata = {}
    if "error_code" in entity_data:
        metadata["error_code"] = entity_data["error_code"]
    if "error_description" in entity_data:
        metadata["error_description"] = entity_data["error_description"]
        
    return NormalizedEvent(
        event_id=event_id,
        entity_type=entity_type,
        entity_id=entity_id,
        customer_id=customer_id,
        event_type=event_type,
        amount=amount,
        currency=currency,
        timestamp=timestamp,
        metadata=metadata
    )
