from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.database import get_db
from backend.app.models.domain import RecoveryCandidate

router = APIRouter()

@router.get("/metrics/revenue-at-risk")
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

@router.get("/metrics/recovery")
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
