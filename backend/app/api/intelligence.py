from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.models.domain import RecoveryPrediction
from backend.app.services.intelligence import run_intelligence_batch, score_candidate

router = APIRouter()

@router.post("/intelligence/run")
def api_run_intelligence(db: Session = Depends(get_db)):
    return run_intelligence_batch(db)

@router.post("/intelligence/{candidate_id}")
def api_score_specific(candidate_id: str, db: Session = Depends(get_db)):
    pred = score_candidate(db, candidate_id)
    return {
        "prediction_id": pred.prediction_id,
        "recommended_action": pred.recommended_action,
        "expected_recovery_value": pred.expected_recovery_value
    }

@router.get("/intelligence/{candidate_id}")
def api_get_prediction(candidate_id: str, db: Session = Depends(get_db)):
    latest = db.query(RecoveryPrediction).filter_by(candidate_id=candidate_id).order_by(RecoveryPrediction.created_at.desc()).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No prediction found for candidate")
        
    return {
        "prediction_id": latest.prediction_id,
        "retry_probability": latest.retry_probability,
        "payment_update_probability": latest.payment_update_probability,
        "escalation_probability": latest.escalation_probability,
        "recommended_action": latest.recommended_action,
        "expected_recovery_value": latest.expected_recovery_value,
        "explanation": latest.explanation,
        "created_at": latest.created_at
    }
