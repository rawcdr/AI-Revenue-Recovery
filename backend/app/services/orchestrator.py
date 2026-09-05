import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.models.domain import RecoveryCandidate, RecoveryPrediction, RecoveryAction, RecoveryOutcome
from backend.app.services.intelligence import score_candidate
from backend.app.services.policy import validate_action
from backend.app.services.simulator import simulate_execution
from backend.app.core.logger import get_logger

logger = get_logger(__name__)

def execute_candidate(db: Session, candidate_id: str):
    candidate = db.query(RecoveryCandidate).filter_by(candidate_id=candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    if candidate.status != "ACTIVE":
        raise HTTPException(status_code=409, detail=f"Candidate {candidate_id} is not ACTIVE (current status: {candidate.status}). Cannot execute action.")
        
    # Phase 4 Integration: Get latest prediction
    prediction = db.query(RecoveryPrediction).filter_by(candidate_id=candidate.candidate_id).order_by(RecoveryPrediction.created_at.desc()).first()
    
    # If no prediction exists, generate one securely
    if not prediction:
        prediction = score_candidate(db, candidate.candidate_id)
        
    action_type = prediction.recommended_action
    attempt_number = (candidate.retry_count or 0) + 1
    idempotency_key = f"{candidate.candidate_id}_{action_type}_{attempt_number}"
    
    # Idempotency check
    existing_action = db.query(RecoveryAction).filter_by(idempotency_key=idempotency_key).first()
    if existing_action:
        raise HTTPException(status_code=409, detail=f"Action for candidate {candidate_id} with key {idempotency_key} already exists.")
        
    # Create action record: PENDING
    action = RecoveryAction(
        action_id=f"act_{uuid.uuid4().hex[:16]}",
        candidate_id=candidate.candidate_id,
        action_type=action_type,
        status="PENDING",
        idempotency_key=idempotency_key,
        attempt_number=attempt_number,
        created_at=datetime.now().isoformat()
    )
    db.add(action)
    db.flush()
    
    # State Transition: VALIDATING
    action.status = "VALIDATING"
    is_approved, policy_reason = validate_action(db, candidate, action_type, attempt_number)
    
    if not is_approved:
        action.status = "BLOCKED"
        action.reason = policy_reason
        action.completed_at = datetime.now().isoformat()
        db.commit()
        
        logger.warning(
            f"Action {action_type} for candidate {candidate.candidate_id} was BLOCKED by policy: {policy_reason}",
            extra={
                "candidate_id": candidate.candidate_id,
                "action_type": action_type,
                "status": "BLOCKED"
            }
        )
        
        # Persist blocked outcome
        outcome = RecoveryOutcome(
            outcome_id=f"out_{uuid.uuid4().hex[:16]}",
            action_id=action.action_id,
            candidate_id=candidate.candidate_id,
            outcome="BLOCKED",
            recovered_amount=0.0,
            failure_reason=policy_reason,
            created_at=datetime.now().isoformat()
        )
        db.add(outcome)
        db.commit()
        return action
        
    action.status = "APPROVED"
    action.reason = policy_reason
    
    # State Transition: EXECUTING
    action.status = "EXECUTING"
    
    sim_result, recovered_amount = simulate_execution(db, candidate, action_type)
    
    if sim_result == "SUCCESS":
        action.status = "SUCCEEDED"
        action.result = "SUCCESS"
        candidate_outcome = "RECOVERED" if action_type != "ESCALATE" else "ESCALATED"
        logger.info(
            f"Action {action_type} SUCCEEDED. Outcome: {candidate_outcome}",
            extra={"candidate_id": candidate.candidate_id, "action_type": action_type, "status": "SUCCEEDED"}
        )
    else:
        action.status = "FAILED"
        action.result = "FAILED"
        candidate_outcome = "NOT_RECOVERED"
        logger.error(
            f"Action {action_type} FAILED.",
            extra={"candidate_id": candidate.candidate_id, "action_type": action_type, "status": "FAILED"}
        )
        
    action.completed_at = datetime.now().isoformat()
    
    # Persist outcome
    outcome = RecoveryOutcome(
        outcome_id=f"out_{uuid.uuid4().hex[:16]}",
        action_id=action.action_id,
        candidate_id=candidate.candidate_id,
        outcome=candidate_outcome,
        recovered_amount=recovered_amount,
        failure_reason=None if sim_result == "SUCCESS" else "Simulated execution failed.",
        created_at=datetime.now().isoformat()
    )
    db.add(outcome)
    
    # Update candidate state
    if action_type == "RETRY":
        candidate.retry_count = attempt_number
        
    if candidate_outcome == "RECOVERED":
        candidate.status = "RESOLVED"
        candidate.state = "RECOVERED"
    elif candidate_outcome == "ESCALATED":
        candidate.status = "RESOLVED"
        candidate.state = "ESCALATED"
        
    db.commit()
    return action

def run_recovery_batch(db: Session):
    candidates = db.query(RecoveryCandidate).filter(
        RecoveryCandidate.status == "ACTIVE"
    ).all()
    
    stats = {
        "status": "completed",
        "processed": 0,
        "actions_created": 0
    }
    
    for c in candidates:
        if stats["processed"] >= settings.RECOVERY_MAX_BATCH:
            break
            
        try:
            execute_candidate(db, c.candidate_id)
            stats["processed"] += 1
            stats["actions_created"] += 1
        except HTTPException as e:
            if e.status_code == 409:
                # Expected if candidate state changed or idempotency hit during batch
                logger.info(f"Skipping candidate {c.candidate_id} during batch: {e.detail}")
                stats["processed"] += 1
            else:
                raise
        
    return stats
