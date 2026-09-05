from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.app.models.domain import ModelRegistry

def get_active_model(db: Session) -> ModelRegistry:
    return db.query(ModelRegistry).filter_by(status="ACTIVE").first()

def get_model(db: Session, version: str) -> ModelRegistry:
    model = db.query(ModelRegistry).filter_by(model_version=version).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model version not found")
    return model

def list_models(db: Session):
    return db.query(ModelRegistry).all()

def promote_model(db: Session, version: str):
    """Explicitly promotes a model to ACTIVE and retires the current ACTIVE model."""
    model_to_promote = db.query(ModelRegistry).filter_by(model_version=version).first()
    
    if not model_to_promote:
        raise ValueError(f"Model version {version} not found in registry.")
        
    if model_to_promote.status != "VALIDATED":
        raise ValueError(f"Model {version} cannot be promoted. Current status is {model_to_promote.status}. Must be VALIDATED.")
        
    current_active = db.query(ModelRegistry).filter_by(status="ACTIVE").first()
    
    if current_active:
        if current_active.model_version == version:
            raise ValueError(f"Model {version} is already ACTIVE.")
        current_active.status = "RETIRED"
        
    model_to_promote.status = "ACTIVE"
    db.commit()
    return True
