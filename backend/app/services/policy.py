from typing import Tuple
from sqlalchemy.orm import Session
from backend.app.models.domain import RecoveryCandidate, Payment

MAX_RETRY_ATTEMPTS = 3
SENSITIVE_FAILURE_CODES = ["suspected_fraud", "customer_dispute", "account_closed"]

def validate_action(db: Session, candidate: RecoveryCandidate, action_type: str, attempt_number: int) -> Tuple[bool, str]:
    """
    Validates if a recommended action is allowed to be executed based on deterministic safety rules.
    Returns (is_approved, reason).
    """
    if candidate.status != "ACTIVE":
        return False, f"Candidate is not ACTIVE (Current status: {candidate.status})."
        
    if action_type == "RETRY":
        # Rule 1: Max retries
        if attempt_number > MAX_RETRY_ATTEMPTS:
            return False, f"Maximum retry attempts reached (Limit: {MAX_RETRY_ATTEMPTS})."
            
        # Rule 2: Block sensitive cases
        if candidate.entity_type == "payment":
            payment = db.query(Payment).filter_by(payment_id=candidate.entity_id).first()
            if payment and payment.error_code in SENSITIVE_FAILURE_CODES:
                return False, f"Action RETRY blocked for sensitive error code: {payment.error_code}."
                
    # ESCALATE is always safe
    if action_type == "ESCALATE":
        return True, "Escalation approved."
        
    # PAYMENT_UPDATE is generally safe, could have rate limits in future
    if action_type == "PAYMENT_UPDATE":
        return True, "Payment update workflow approved."
        
    return True, "Policy approved."
