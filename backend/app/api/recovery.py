from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.services.recovery_queue import get_recovery_queue

router = APIRouter()

@router.get("/recovery/queue")
def read_recovery_queue(db: Session = Depends(get_db)):
    return get_recovery_queue(db)
