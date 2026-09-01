from sqlalchemy.orm import Session
from backend.app.models.domain import Payment, Subscription, Customer

def get_recovery_queue(db: Session):
    failed_payments = db.query(Payment, Customer).join(Customer, Payment.customer_id == Customer.customer_id).filter(Payment.status == 'failed').all()
    
    subs = db.query(Subscription, Customer).join(Customer, Subscription.customer_id == Customer.customer_id).filter(Subscription.status.in_(['pending', 'halted'])).all()
    
    queue = []
    
    def get_factor(segment):
        if segment == 'high_value': return 1.5
        if segment == 'standard': return 1.0
        return 0.8
        
    for p, c in failed_payments:
        score = p.amount * get_factor(c.customer_segment)
        queue.append({
            "entity_type": "payment",
            "entity_id": p.payment_id,
            "customer_id": c.customer_id,
            "amount": p.amount,
            "currency": p.currency,
            "status": p.status,
            "priority_score": score,
            "timestamp": p.failed_at
        })
        
    for s, c in subs:
        score = s.mrr_value * get_factor(c.customer_segment)
        queue.append({
            "entity_type": "subscription",
            "entity_id": s.subscription_id,
            "customer_id": c.customer_id,
            "amount": s.mrr_value,
            "currency": s.currency,
            "status": s.status,
            "priority_score": score,
            "timestamp": s.halted_at if s.status == 'halted' else s.pending_since
        })
        
    queue.sort(key=lambda x: x['priority_score'], reverse=True)
    return queue
