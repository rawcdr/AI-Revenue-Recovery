from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "revenue-recovery-agent"
    }

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.models.domain import ModelRegistry, RecoveryCandidate

@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    try:
        # Check DB connectivity and required tables
        db.query(RecoveryCandidate).first()
        
        # Check active model
        active = db.query(ModelRegistry).filter_by(status="ACTIVE").first()
        if not active:
            return {"status": "not_ready", "reason": "No ACTIVE model in registry"}
            
        return {
            "status": "ready",
            "active_model": active.model_version
        }
    except Exception as e:
        return {"status": "not_ready", "reason": str(e)}
