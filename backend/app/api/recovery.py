from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.services.recovery_queue import get_recovery_queue

router = APIRouter(tags=["Recovery Execution"])

@router.get(
    "/recovery/queue",
    summary="Get Recovery Queue",
    description="Retrieves a list of all active recovery candidates requiring intervention."
)
def read_recovery_queue(db: Session = Depends(get_db)):
    return get_recovery_queue(db)

from backend.app.services.orchestrator import execute_candidate, run_recovery_batch
from backend.app.models.domain import RecoveryAction

@router.post(
    "/recovery/execute",
    summary="Execute Batch Recovery",
    description="Deterministically executes the recommended recovery action for all ACTIVE candidates."
)
def execute_batch(db: Session = Depends(get_db)):
    return run_recovery_batch(db)

@router.post(
    "/recovery/{candidate_id}/execute",
    summary="Execute Single Recovery Action",
    description="Simulates the execution of a recovery action for a specific candidate. Respects policy bounds and idempotency."
)
def execute_single(candidate_id: str, db: Session = Depends(get_db)):
    action = execute_candidate(db, candidate_id)
    return {
        "action_id": action.action_id,
        "action_type": action.action_type,
        "status": action.status,
        "result": action.result
    }

@router.get("/recovery/{candidate_id}/actions")
def get_candidate_actions(candidate_id: str, db: Session = Depends(get_db)):
    actions = db.query(RecoveryAction).filter_by(candidate_id=candidate_id).order_by(RecoveryAction.created_at.desc()).all()
    return [
        {
            "action_id": a.action_id,
            "action_type": a.action_type,
            "status": a.status,
            "attempt_number": a.attempt_number,
            "reason": a.reason,
            "result": a.result,
            "created_at": a.created_at,
            "completed_at": a.completed_at
        } for a in actions
    ]
