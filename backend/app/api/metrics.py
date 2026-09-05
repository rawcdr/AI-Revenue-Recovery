from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.database import get_db
from backend.app.models.domain import RecoveryCandidate

router = APIRouter(tags=["Metrics & Feedback"])

@router.get(
    "/metrics/revenue-at-risk",
    summary="Get Revenue At Risk",
    description="Calculates the total aggregate revenue tied to active Recovery Candidates."
)
def get_revenue_at_risk(db: Session = Depends(get_db)):
    active_candidates = db.query(RecoveryCandidate).filter(RecoveryCandidate.status == "ACTIVE").all()
    revenue_at_risk = sum(c.amount for c in active_candidates)
    
    failed_payment_count = sum(1 for c in active_candidates if c.entity_type == "payment")
    subscription_count = sum(1 for c in active_candidates if c.entity_type == "subscription")
    
    return {
        "revenue_at_risk": revenue_at_risk,
        "currency": "INR",
        "failed_payment_count": failed_payment_count,
        "subscription_count": subscription_count
    }

from backend.app.models.domain import RecoveryAction, RecoveryOutcome

@router.get(
    "/metrics/recovery",
    summary="Get Recovery Action Metrics",
    description="Computes action-level success, block, and failure rates from the simulated recovery actions."
)
def get_recovery_metrics(db: Session = Depends(get_db)):
    actions = db.query(RecoveryAction).all()
    outcomes = db.query(RecoveryOutcome).all()
    
    total_actions = len(actions)
    successful_actions = sum(1 for a in actions if a.status == "SUCCEEDED")
    failed_actions = sum(1 for a in actions if a.status == "FAILED")
    blocked_actions = sum(1 for a in actions if a.status == "BLOCKED")
    
    # We define an "escalation" as an action where type is ESCALATE, or outcome is ESCALATED
    escalations = sum(1 for o in outcomes if o.outcome == "ESCALATED")
    
    # Revenue recovered (deduplicated by candidate to avoid double counting)
    recovered_candidates_amounts = {}
    for o in outcomes:
        if o.outcome == "RECOVERED":
            recovered_candidates_amounts[o.candidate_id] = o.recovered_amount
    revenue_recovered = sum(recovered_candidates_amounts.values())
    
    # Action metrics
    action_success_rate = successful_actions / total_actions if total_actions > 0 else 0.0
    
    # Recovery rate (candidates fully recovered / candidates ever attempted)
    attempted_candidates = set(a.candidate_id for a in actions)
    recovered_candidates = set(o.candidate_id for o in outcomes if o.outcome == "RECOVERED")
    
    recovery_rate = len(recovered_candidates) / len(attempted_candidates) if attempted_candidates else 0.0
    
    # Revenue by action type
    revenue_by_action = {}
    for o in outcomes:
        if o.outcome == "RECOVERED":
            act = db.query(RecoveryAction).filter_by(action_id=o.action_id).first()
            if act:
                revenue_by_action[act.action_type] = revenue_by_action.get(act.action_type, 0) + o.recovered_amount
                
    return {
        "total_recovery_actions": total_actions,
        "successful_actions": successful_actions,
        "failed_actions": failed_actions,
        "blocked_actions": blocked_actions,
        "escalations": escalations,
        "revenue_recovered": revenue_recovered,
        "recovery_rate": recovery_rate,
        "action_success_rate": action_success_rate,
        "recovery_amount_by_action_type": revenue_by_action
    }

from backend.app.models.domain import RecoveryFeedback

@router.get(
    "/metrics/feedback",
    summary="Get Machine Learning Feedback Metrics",
    description="Aggregates end-to-end feedback loops, tracking action performance, prediction calibration buckets, and revenue-weighted recovery outcomes."
)
def get_feedback_metrics(db: Session = Depends(get_db)):
    feedbacks = db.query(RecoveryFeedback).all()
    
    # 1. Action Performance
    action_metrics = {}
    for action in ["RETRY", "PAYMENT_UPDATE", "ESCALATE"]:
        fbs = [f for f in feedbacks if f.actual_action == action]
        if not fbs:
            continue
        successes = sum(1 for f in fbs if f.action_status == "SUCCEEDED")
        recovered = sum(1 for f in fbs if f.actual_outcome == "RECOVERED")
        revenue = sum(f.recovered_amount for f in fbs if f.actual_outcome == "RECOVERED")
        
        action_metrics[action] = {
            "count": len(fbs),
            "successful_executions": successes,
            "failed_executions": sum(1 for f in fbs if f.action_status == "FAILED"),
            "recovered_count": recovered,
            "not_recovered_count": sum(1 for f in fbs if f.actual_outcome == "NOT_RECOVERED"),
            "recovery_rate": recovered / len(fbs) if len(fbs) > 0 else 0.0,
            "revenue_recovered": revenue
        }
        
    # 2. Calibration (buckets: 0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0)
    buckets = {
        "0.0-0.2": [], "0.2-0.4": [], "0.4-0.6": [], "0.6-0.8": [], "0.8-1.0": []
    }
    
    for f in feedbacks:
        p = f.recommended_probability
        if p <= 0.2: buckets["0.0-0.2"].append(f)
        elif p <= 0.4: buckets["0.2-0.4"].append(f)
        elif p <= 0.6: buckets["0.4-0.6"].append(f)
        elif p <= 0.8: buckets["0.6-0.8"].append(f)
        else: buckets["0.8-1.0"].append(f)
        
    calibration = {}
    for b_name, b_list in buckets.items():
        if not b_list:
            continue
        avg_prob = sum(f.recommended_probability for f in b_list) / len(b_list)
        rec_rate = sum(1 for f in b_list if f.actual_outcome == "RECOVERED") / len(b_list)
        calibration[b_name] = {
            "prediction_count": len(b_list),
            "average_predicted_probability": avg_prob,
            "actual_recovery_rate": rec_rate
        }
        
    # 3. Revenue-weighted evaluation
    revenue_metrics = {}
    total_expected = sum(f.expected_recovery_value for f in feedbacks)
    
    # deduplicate by candidate to avoid double counting revenue recovered
    recovered_candidates_amounts = {}
    for f in feedbacks:
        if f.actual_outcome == "RECOVERED":
            recovered_candidates_amounts[f.candidate_id] = f.recovered_amount
    total_realized = sum(recovered_candidates_amounts.values())
    
    # We estimate total revenue at risk by summing up unique candidates in the feedback
    # Note: feedback represents completed decisions.
    unique_candidates_risk = {}
    for f in feedbacks:
        # Reconstruct original risk by expected / prob, or simply amount if stored. We can estimate.
        if f.recommended_probability > 0:
            val = f.expected_recovery_value / f.recommended_probability
            unique_candidates_risk[f.candidate_id] = val
    total_risk = sum(unique_candidates_risk.values())
    
    revenue_metrics = {
        "total_revenue_at_risk": total_risk,
        "expected_recovery_value": total_expected,
        "realized_recovery_value": total_realized,
        "recovery_rate_by_value": (total_realized / total_risk) if total_risk > 0 else 0.0
    }
    
    return {
        "action_performance": action_metrics,
        "calibration": calibration,
        "revenue_metrics": revenue_metrics
    }

@router.get(
    "/metrics/recent-activity",
    summary="Get Recent Activity",
    description="Returns the 10 most recent recovery outcomes and their explanations."
)
def get_recent_activity(db: Session = Depends(get_db)):
    from backend.app.models.domain import RecoveryPrediction
    feedbacks = db.query(RecoveryFeedback).order_by(RecoveryFeedback.created_at.desc()).limit(10).all()
    
    activity = []
    for f in feedbacks:
        pred = db.query(RecoveryPrediction).filter_by(prediction_id=f.prediction_id).first()
        activity.append({
            "candidate_id": f.candidate_id,
            "action": f.actual_action,
            "result": f.actual_outcome,
            "recovered_amount": f.recovered_amount,
            "timestamp": f.created_at,
            "explanation": pred.explanation if pred else "No explanation available"
        })
    return activity
