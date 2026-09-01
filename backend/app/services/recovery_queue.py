from sqlalchemy.orm import Session
from backend.app.models.domain import RecoveryCandidate

def get_recovery_queue(db: Session):
    candidates = db.query(RecoveryCandidate).filter(RecoveryCandidate.status == "ACTIVE").order_by(RecoveryCandidate.priority_score.desc()).all()
    
    queue = []
    for c in candidates:
        queue.append({
            "candidate_id": c.candidate_id,
            "entity_type": c.entity_type,
            "entity_id": c.entity_id,
            "customer_id": c.customer_id,
            "candidate_type": c.candidate_type,
            "state": c.state,
            "amount": c.amount,
            "currency": c.currency,
            "retry_count": c.retry_count,
            "priority_score": c.priority_score,
            "severity": c.severity,
            "detection_reason": c.detection_reason,
            "detected_at": c.detected_at
        })
        
    return queue
