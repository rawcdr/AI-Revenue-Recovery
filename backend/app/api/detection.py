from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.services.detection import run_detection

router = APIRouter()

@router.post("/detection/run")
def api_run_detection(db: Session = Depends(get_db)):
    return run_detection(db)
