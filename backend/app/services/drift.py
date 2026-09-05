from sqlalchemy.orm import Session
from backend.app.models.domain import RecoveryFeedback

def calculate_drift_and_retraining(db: Session, version: str):
    """
    Deterministically evaluates data drift and performance drift based on recovery_feedback.
    Recommends retraining ONLY if conditions are met.
    """
    feedbacks = db.query(RecoveryFeedback).filter_by(model_version=version).all()
    
    if len(feedbacks) < 50:
        return {
            "drift_status": "NO_DRIFT",
            "retraining_recommendation": "NO_RETRAINING_REQUIRED",
            "reason": f"Insufficient feedback data ({len(feedbacks)} < 50) for reliable drift detection."
        }
        
    # Example logic: we split feedback chronologically into 'old' (first 50%) and 'new' (last 50%)
    # In a real scenario, 'old' would be the training dataset distribution, but here we just check recent shift.
    
    # Sort feedbacks by created_at
    feedbacks.sort(key=lambda x: x.created_at)
    
    midpoint = len(feedbacks) // 2
    old_feedbacks = feedbacks[:midpoint]
    new_feedbacks = feedbacks[midpoint:]
    
    # Calculate recovery rate for old vs new
    def calc_rate(fbs):
        successes = sum(1 for f in fbs if f.actual_outcome == "RECOVERED")
        return successes / len(fbs) if fbs else 0.0
        
    old_rate = calc_rate(old_feedbacks)
    new_rate = calc_rate(new_feedbacks)
    
    # Performance Drift Check
    # If the new rate is 15% worse (absolute) than the old rate, trigger performance drift.
    performance_drift = False
    if old_rate - new_rate >= 0.15:
        performance_drift = True
        
    # Data Drift Check
    # Compare categorical distributions (e.g., actual_action)
    def action_dist(fbs):
        dist = {}
        for f in fbs:
            dist[f.actual_action] = dist.get(f.actual_action, 0) + 1
        for k in dist:
            dist[k] /= len(fbs)
        return dist
        
    old_dist = action_dist(old_feedbacks)
    new_dist = action_dist(new_feedbacks)
    
    data_drift = False
    for k, v in old_dist.items():
        new_v = new_dist.get(k, 0.0)
        # If absolute difference in category distribution > 20%
        if abs(v - new_v) > 0.20:
            data_drift = True
            
    status = "NO_DRIFT"
    if performance_drift and data_drift:
        status = "DATA_AND_PERFORMANCE_DRIFT"
    elif performance_drift:
        status = "PERFORMANCE_DRIFT"
    elif data_drift:
        status = "DATA_DRIFT"
        
    recommendation = "NO_RETRAINING_REQUIRED"
    if performance_drift:
        recommendation = "RETRAIN_RECOMMENDED"
        
    return {
        "drift_status": status,
        "retraining_recommendation": recommendation,
        "reason": f"Performance shifted from {old_rate:.2%} to {new_rate:.2%}." if performance_drift else "Stable performance.",
        "old_rate": old_rate,
        "new_rate": new_rate
    }
