from typing import Tuple
from sqlalchemy.orm import Session
from backend.app.models.domain import RecoveryCandidate, Payment

def simulate_execution(db: Session, candidate: RecoveryCandidate, action_type: str) -> Tuple[str, float]:
    """
    Safely simulates a recovery action based on deterministic boundaries.
    Returns (result, amount_recovered).
    Result is "SUCCESS" or "FAILED".
    """
    if action_type == "ESCALATE":
        # Escalation is a workflow transition, it always "succeeds" in terms of executing the escalation.
        return "SUCCESS", 0.0
        
    error_code = "unknown"
    if candidate.entity_type == "payment":
        payment = db.query(Payment).filter_by(payment_id=candidate.entity_id).first()
        if payment:
            error_code = payment.error_code or "unknown"
            
    # Deterministic simulation logic
    if action_type == "RETRY":
        if error_code == "network_error":
            return "SUCCESS", candidate.amount
        elif error_code == "insufficient_funds":
            # Using the candidate ID hash to deterministically simulate ~50% success
            val = hash(candidate.candidate_id) % 100
            if val < 50:
                return "SUCCESS", candidate.amount
            return "FAILED", 0.0
        elif error_code == "expired_card":
            # Retrying an expired card almost always fails
            return "FAILED", 0.0
        else:
            return "FAILED", 0.0
            
    if action_type == "PAYMENT_UPDATE":
        if error_code == "expired_card":
            return "SUCCESS", candidate.amount
        else:
            # Payment updates generally have high success when completed, 
            # simulating a 70% conversion rate.
            val = hash(candidate.candidate_id) % 100
            if val < 70:
                return "SUCCESS", candidate.amount
            return "FAILED", 0.0
            
    return "FAILED", 0.0
