from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.models.domain import Event
import json

router = APIRouter()

@router.get("/events")
def get_events(limit: int = 100, db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.timestamp.desc()).limit(limit).all()
    # Need to convert metadata string to dict for JSON serialization
    results = []
    for e in events:
        d = e.__dict__.copy()
        if "_sa_instance_state" in d:
            del d["_sa_instance_state"]
        try:
            d["metadata"] = json.loads(d.pop("metadata_"))
        except:
            d["metadata"] = {}
        results.append(d)
    return results
