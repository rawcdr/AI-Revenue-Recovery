import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.models.domain import RecoveryCandidate, RecoveryPrediction, Payment, Customer
from backend.app.intelligence.predictor import RecoveryPredictor
from backend.app.intelligence.scoring import score_predictions
from backend.app.intelligence.explainability import generate_explanation

# Cache the predictor instance in memory to avoid reloading models on every request
_predictor_instance = None

def get_predictor():
    global _predictor_instance
    if _predictor_instance is None:
        try:
            _predictor_instance = RecoveryPredictor()
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
    return _predictor_instance

def build_inference_features(db: Session, candidate: RecoveryCandidate) -> dict:
    customer = db.query(Customer).filter_by(customer_id=candidate.customer_id).first()
    
    # Base feature dictionary expected by the model pipeline
    features = {
        'customer_segment': customer.customer_segment if customer else 'standard',
        'amount_relative': 1.0, # Will be derived
        'retry_count': candidate.retry_count or 0,
        'hour': datetime.fromisoformat(candidate.detected_at).hour if candidate.detected_at else 12,
        'day_of_week': datetime.fromisoformat(candidate.detected_at).weekday() if candidate.detected_at else 0,
        'hist_payment_count': 0,
        'hist_success_rate': 0.0,
        'payment_method': 'card',
        'error_code': 'unknown'
    }
    
    # In a real app we'd calculate history dynamically from DB
    # For now we mock reasonable historical defaults since we don't have historical aggregates in Phase 3
    features['hist_payment_count'] = 10
    features['hist_success_rate'] = 0.8
    
    if candidate.entity_type == "payment":
        payment = db.query(Payment).filter_by(payment_id=candidate.entity_id).first()
        if payment:
            features['payment_method'] = payment.payment_method or 'card'
            features['error_code'] = payment.error_code or 'unknown'
            
    # Calculate amount relative
    features['amount_relative'] = 1.0
            
    return features

def score_candidate(db: Session, candidate_id: str):
    candidate = db.query(RecoveryCandidate).filter_by(candidate_id=candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    predictor = get_predictor()
    features = build_inference_features(db, candidate)
    
    probs = predictor.predict(features)
    action, expected_value = score_predictions(candidate.amount, probs)
    explanation = generate_explanation(action, features)
    
    prediction = RecoveryPrediction(
        prediction_id=f"pred_{uuid.uuid4().hex[:16]}",
        candidate_id=candidate.candidate_id,
        model_version="recovery-model-v1",
        feature_version="feature-schema-v1",
        retry_probability=probs['retry_probability'],
        payment_update_probability=probs['payment_update_probability'],
        escalation_probability=probs['escalation_probability'],
        recommended_action=action,
        expected_recovery_value=expected_value,
        explanation=explanation,
        created_at=datetime.now().isoformat()
    )
    
    db.add(prediction)
    db.commit()
    return prediction

def run_intelligence_batch(db: Session):
    candidates = db.query(RecoveryCandidate).filter(
        RecoveryCandidate.status == "ACTIVE"
    ).all()
    
    stats = {
        "status": "completed",
        "processed": 0
    }
    
    for c in candidates:
        if stats["processed"] >= settings.INTELLIGENCE_MAX_BATCH:
            break
            
        # Deduplication Check
        existing = db.query(RecoveryPrediction).filter_by(candidate_id=c.candidate_id).first()
        if existing:
            continue
            
        score_candidate(db, c.candidate_id)
        stats["processed"] += 1
        
    return stats
