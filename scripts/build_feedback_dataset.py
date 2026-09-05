import os
import sys
import uuid
import csv
from datetime import datetime, timezone

# Add the project root to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.database import SessionLocal, Base, engine
from backend.app.models.domain import RecoveryPrediction, RecoveryAction, RecoveryOutcome, RecoveryFeedback

def build_feedback():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # 1. Fetch completed outcomes and link them to actions, predictions, and candidates
    outcomes = db.query(RecoveryOutcome).all()
    
    feedback_entries = []
    
    for outcome in outcomes:
        # Check if already in feedback to avoid duplicate feedback rows for the same outcome
        existing = db.query(RecoveryFeedback).filter_by(actual_outcome=outcome.outcome, action_id=outcome.action_id).first()
        if existing:
            continue
            
        action = db.query(RecoveryAction).filter_by(action_id=outcome.action_id).first()
        if not action:
            continue
            
        prediction = db.query(RecoveryPrediction).filter_by(candidate_id=action.candidate_id).order_by(RecoveryPrediction.created_at.desc()).first()
        if not prediction:
            continue
            
        prob = 0.0
        if prediction.recommended_action == "RETRY":
            prob = prediction.retry_probability
        elif prediction.recommended_action == "PAYMENT_UPDATE":
            prob = prediction.payment_update_probability
        elif prediction.recommended_action == "ESCALATE":
            prob = prediction.escalation_probability
            
        fb = RecoveryFeedback(
            feedback_id=f"fb_{uuid.uuid4().hex[:16]}",
            candidate_id=outcome.candidate_id,
            prediction_id=prediction.prediction_id,
            action_id=action.action_id,
            model_version=prediction.model_version,
            feature_version=prediction.feature_version,
            recommended_action=prediction.recommended_action,
            recommended_probability=prob,
            expected_recovery_value=prediction.expected_recovery_value,
            actual_action=action.action_type,
            action_status=action.status,
            actual_outcome=outcome.outcome,
            recovered_amount=outcome.recovered_amount,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        db.add(fb)
        feedback_entries.append(fb)
        
    if feedback_entries:
        db.commit()
        print(f"Added {len(feedback_entries)} new feedback entries to database.")
    else:
        print("No new feedback entries to add to database.")
        
    # 2. Generate CSV
    feedback_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "feedback")
    os.makedirs(feedback_dir, exist_ok=True)
    
    csv_path = os.path.join(feedback_dir, "recovery_feedback.csv")
    all_feedback = db.query(RecoveryFeedback).all()
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "candidate_id", "model_version", "feature_version", "action", 
            "predicted_probability", "expected_recovery_value", 
            "actual_outcome", "recovered_amount"
        ])
        
        for fb in all_feedback:
            writer.writerow([
                fb.candidate_id, fb.model_version, fb.feature_version, fb.actual_action,
                fb.recommended_probability, fb.expected_recovery_value,
                fb.actual_outcome, fb.recovered_amount
            ])
            
    print(f"Generated feedback dataset with {len(all_feedback)} rows at {csv_path}")
    print("NOTE: LEAKAGE PROTECTION - Historical outcomes are labels only and must NOT be used as inference features.")
    db.close()

if __name__ == "__main__":
    build_feedback()
