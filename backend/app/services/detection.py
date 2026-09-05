import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.models.domain import Payment, Subscription, Customer, RecoveryCandidate

def get_severity(error_code: str) -> str:
    if not error_code:
        return "MEDIUM"
    if error_code in ["network_error", "gateway_failure", "bank_timeout"]:
        return "LOW"
    elif error_code in ["insufficient_funds", "card_declined", "expired_card", "invalid_payment_method"]:
        return "MEDIUM"
    elif error_code in ["customer_dispute", "suspected_fraud", "account_closed"]:
        return "HIGH"
    return "MEDIUM"

def get_priority_score(amount: float, customer_segment: str, state_factor: float, retry_count: int) -> float:
    customer_factor = 1.0
    if customer_segment == "high_value":
        customer_factor = 1.5
    elif customer_segment == "new":
        customer_factor = 0.8
        
    retry_factor = 1.0
    if retry_count == 1:
        retry_factor = 1.1
    elif retry_count == 2:
        retry_factor = 1.2
    elif retry_count >= 3:
        retry_factor = 0.5
        
    return amount * customer_factor * state_factor * retry_factor

from backend.app.core.logger import get_logger

logger = get_logger(__name__)

def run_detection(db: Session):
    stats = {
        "new_candidates": 0,
        "updated_candidates": 0,
        "resolved_candidates": 0
    }
    
    customers = {c.customer_id: c for c in db.query(Customer).all()}
    active_candidates = {c.entity_id: c for c in db.query(RecoveryCandidate).filter(RecoveryCandidate.status == "ACTIVE").all()}
    seen_entities = set()
    
    # 1. Process Payments
    payments = db.query(Payment).all()
    for p in payments:
        if p.status == "failed":
            c = customers.get(p.customer_id)
            if not c:
                continue
                
            priority = get_priority_score(p.amount, c.customer_segment, 1.0, p.retry_count or 0)
            severity = get_severity(p.error_code)
            reason = "Payment status is failed and the payment has not been captured."
            
            seen_entities.add(p.payment_id)
            existing = active_candidates.get(p.payment_id)
            if existing:
                if existing.priority_score != priority or existing.retry_count != p.retry_count:
                    existing.state = "FAILED"
                    existing.priority_score = priority
                    existing.retry_count = p.retry_count
                    stats["updated_candidates"] += 1
            else:
                new_cand = RecoveryCandidate(
                    candidate_id=f"cndt_{uuid.uuid4().hex[:16]}",
                    entity_type="payment",
                    entity_id=p.payment_id,
                    customer_id=p.customer_id,
                    candidate_type="PAYMENT_FAILURE",
                    state="FAILED",
                    amount=p.amount,
                    currency=p.currency,
                    retry_count=p.retry_count or 0,
                    priority_score=priority,
                    severity=severity,
                    detection_reason=reason,
                    detected_at=datetime.now().isoformat(),
                    status="ACTIVE"
                )
                db.add(new_cand)
                stats["new_candidates"] += 1
                logger.info(f"New candidate detected: {p.payment_id}", extra={"candidate_id": new_cand.candidate_id})
                
        elif p.status == "captured" or p.status == "successful":
            existing = active_candidates.get(p.payment_id)
            if existing:
                existing.status = "RESOLVED"
                stats["resolved_candidates"] += 1
                seen_entities.add(p.payment_id)
                
    # 2. Process Subscriptions
    subs = db.query(Subscription).all()
    for s in subs:
        if s.status in ["pending", "halted"]:
            c = customers.get(s.customer_id)
            if not c:
                continue
                
            state_factor = 1.2 if s.status == "pending" else 1.5
            priority = get_priority_score(s.mrr_value, c.customer_segment, state_factor, s.auth_attempts or 0)
            severity = get_severity(s.failure_reason)
            reason = f"Subscription has transitioned to {s.status} state and requires recovery attention." if s.status == "halted" else "Subscription is in pending state with an outstanding recovery amount."
            candidate_type = "SUBSCRIPTION_HALTED" if s.status == "halted" else "SUBSCRIPTION_PENDING"
            
            seen_entities.add(s.subscription_id)
            existing = active_candidates.get(s.subscription_id)
            if existing:
                if existing.state != s.status.upper() or existing.priority_score != priority or existing.retry_count != s.auth_attempts:
                    existing.state = s.status.upper()
                    existing.candidate_type = candidate_type
                    existing.priority_score = priority
                    existing.retry_count = s.auth_attempts
                    stats["updated_candidates"] += 1
            else:
                new_cand = RecoveryCandidate(
                    candidate_id=f"cndt_{uuid.uuid4().hex[:16]}",
                    entity_type="subscription",
                    entity_id=s.subscription_id,
                    customer_id=s.customer_id,
                    candidate_type=candidate_type,
                    state=s.status.upper(),
                    amount=s.mrr_value,
                    currency=s.currency,
                    retry_count=s.auth_attempts or 0,
                    priority_score=priority,
                    severity=severity,
                    detection_reason=reason,
                    detected_at=datetime.now().isoformat(),
                    status="ACTIVE"
                )
                db.add(new_cand)
                stats["new_candidates"] += 1
                logger.info(f"New subscription candidate detected: {s.subscription_id}", extra={"candidate_id": new_cand.candidate_id})
        elif s.status == "active":
             existing = active_candidates.get(s.subscription_id)
             if existing:
                 existing.status = "RESOLVED"
                 stats["resolved_candidates"] += 1
                 seen_entities.add(s.subscription_id)
                 
    db.commit()
    
    active_count = db.query(RecoveryCandidate).filter(RecoveryCandidate.status == "ACTIVE").count()
    # Sum in python to ensure accurate floating addition across items
    active_list = db.query(RecoveryCandidate).filter(RecoveryCandidate.status == "ACTIVE").all()
    revenue_at_risk = sum(c.amount for c in active_list)
    
    stats["active_candidates"] = active_count
    stats["revenue_at_risk"] = revenue_at_risk
    stats["status"] = "completed"
    
    return stats
