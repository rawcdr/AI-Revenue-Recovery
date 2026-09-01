import csv
import random
from datetime import datetime, timedelta
import uuid
import os

SEED = 42
random.seed(SEED)

try:
    from faker import Faker
    fake = Faker('en_IN')
    Faker.seed(SEED)
except ImportError:
    print("Faker is not installed. Please run pip install faker")
    exit(1)

OUTPUT_DIR = "data/generated"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configuration
NUM_CUSTOMERS = 200
NUM_PAYMENTS = 300
NUM_SUBSCRIPTIONS = 100
NUM_CHECKOUTS = 150
CURRENCY = "INR"

def generate_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:16]}"

def random_date(start, end):
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

def get_amount_choices():
    return [499, 999, 1499, 2499, 4999, 9999, 19999]

def generate_customers():
    customers = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    segments = ["new", "standard", "high_value"]
    tiers = ["low", "medium", "high"]
    methods = ["card", "upi", "netbanking", "wallet"]
    
    for _ in range(NUM_CUSTOMERS):
        created_at = random_date(start_date, end_date - timedelta(days=5))
        segment = random.choices(segments, weights=[0.2, 0.6, 0.2])[0]
        customer = {
            "customer_id": generate_id("cust"),
            "customer_name": fake.name(),
            "customer_segment": segment,
            "customer_ltv": 0, # Will be updated
            "risk_tier": random.choices(tiers, weights=[0.7, 0.2, 0.1])[0],
            "default_payment_method": random.choice(methods),
            "created_at": created_at.isoformat()
        }
        customers.append(customer)
    return customers

# Failure taxonomy definitions
FAILURE_CAUSES = [
    ("insufficient_funds", 0.25, True, "RETRY", "bank", "BAD_REQUEST_ERROR"),
    ("card_declined", 0.20, True, "RETRY", "bank", "BAD_REQUEST_ERROR"),
    ("gateway_failure", 0.15, True, "RETRY", "gateway", "GATEWAY_ERROR"),
    ("network_error", 0.10, True, "RETRY", "business", "SERVER_ERROR"),
    ("expired_card", 0.10, True, "PAYMENT_UPDATE", "customer", "BAD_REQUEST_ERROR"),
    ("invalid_payment_method", 0.07, True, "PAYMENT_UPDATE", "customer", "BAD_REQUEST_ERROR"),
    ("bank_timeout", 0.05, True, "RETRY", "bank", "GATEWAY_ERROR"),
    ("customer_dispute", 0.03, False, "ESCALATE", "customer", "BAD_REQUEST_ERROR"),
    ("suspected_fraud", 0.03, False, "ESCALATE", "bank", "BAD_REQUEST_ERROR"),
    ("account_closed", 0.02, False, "ESCALATE", "bank", "BAD_REQUEST_ERROR")
]

def generate_payments(customers, events):
    payments = []
    
    causes = [f[0] for f in FAILURE_CAUSES]
    weights = [f[1] for f in FAILURE_CAUSES]
    cause_map = {f[0]: f for f in FAILURE_CAUSES}
    
    for i in range(NUM_PAYMENTS):
        customer = random.choice(customers)
        cust_created = datetime.fromisoformat(customer["created_at"])
        end_date = datetime.now()
        created_at = random_date(cust_created, end_date)
        
        # Correlate amounts somewhat with segment
        amount_choices = get_amount_choices()
        if customer["customer_segment"] == "high_value":
            amount = random.choice(amount_choices[4:])
        else:
            amount = random.choice(amount_choices[:4])
            
        is_failed = random.random() < 0.3 # 30% failure rate
        
        payment = {
            "payment_id": generate_id("pay"),
            "customer_id": customer["customer_id"],
            "amount": amount,
            "currency": CURRENCY,
            "payment_method": customer["default_payment_method"],
            "status": "failed" if is_failed else "captured",
            "created_at": created_at.isoformat(),
            "failed_at": "",
            "retry_count": 0,
            "error_code": "",
            "error_source": "",
            "recoverable": "",
            "ground_truth_root_cause": "",
            "ground_truth_action": ""
        }
        
        events.append({
            "event_id": generate_id("evt"),
            "entity_type": "payment",
            "entity_id": payment["payment_id"],
            "customer_id": payment["customer_id"],
            "event_type": "payment.created",
            "amount": amount,
            "currency": CURRENCY,
            "timestamp": created_at.isoformat(),
            "metadata": "{}"
        })
        
        if is_failed:
            failed_at = created_at + timedelta(seconds=random.randint(10, 60))
            cause_key = random.choices(causes, weights=weights)[0]
            cause_info = cause_map[cause_key]
            
            payment["failed_at"] = failed_at.isoformat()
            payment["retry_count"] = random.randint(0, 2)
            payment["error_code"] = cause_info[5]
            payment["error_source"] = cause_info[4]
            # Some realism noise on recoverability
            recoverable = cause_info[2]
            if cause_key == "card_declined" and random.random() < 0.1:
                recoverable = False # Sometimes unrecoverable
            if cause_key == "gateway_failure" and random.random() < 0.05:
                recoverable = False
                
            payment["recoverable"] = str(recoverable).lower()
            payment["ground_truth_root_cause"] = cause_key
            payment["ground_truth_action"] = cause_info[3] if recoverable else "ESCALATE"
            
            events.append({
                "event_id": generate_id("evt"),
                "entity_type": "payment",
                "entity_id": payment["payment_id"],
                "customer_id": payment["customer_id"],
                "event_type": "payment.failed",
                "amount": amount,
                "currency": CURRENCY,
                "timestamp": failed_at.isoformat(),
                "metadata": f'{{"reason": "{cause_key}"}}'
            })
        else:
            auth_at = created_at + timedelta(seconds=random.randint(2, 10))
            capture_at = auth_at + timedelta(seconds=random.randint(1, 5))
            events.append({
                "event_id": generate_id("evt"),
                "entity_type": "payment",
                "entity_id": payment["payment_id"],
                "customer_id": payment["customer_id"],
                "event_type": "payment.authorized",
                "amount": amount,
                "currency": CURRENCY,
                "timestamp": auth_at.isoformat(),
                "metadata": "{}"
            })
            events.append({
                "event_id": generate_id("evt"),
                "entity_type": "payment",
                "entity_id": payment["payment_id"],
                "customer_id": payment["customer_id"],
                "event_type": "payment.captured",
                "amount": amount,
                "currency": CURRENCY,
                "timestamp": capture_at.isoformat(),
                "metadata": "{}"
            })
            customer["customer_ltv"] += amount
            
        payments.append(payment)
        
    return payments

def generate_subscriptions(customers, events):
    subscriptions = []
    plans = [("plan_basic", 499), ("plan_pro", 1499), ("plan_business", 4999)]
    
    for i in range(NUM_SUBSCRIPTIONS):
        customer = random.choice(customers)
        cust_created = datetime.fromisoformat(customer["created_at"])
        end_date = datetime.now() - timedelta(days=10)
        if cust_created >= end_date:
            end_date = datetime.now()
        created_at = random_date(cust_created, end_date)
        plan_id, mrr = random.choice(plans)
        
        status_roll = random.random()
        if status_roll < 0.70:
            status = "active"
        elif status_roll < 0.85:
            status = "pending"
        else:
            status = "halted"
            
        sub = {
            "subscription_id": generate_id("sub"),
            "customer_id": customer["customer_id"],
            "plan_id": plan_id,
            "mrr_value": mrr,
            "currency": CURRENCY,
            "status": status,
            "auth_attempts": 0,
            "paid_count": random.randint(1, 5),
            "created_at": created_at.isoformat(),
            "pending_since": "",
            "halted_at": "",
            "failure_reason": "",
            "recoverable": "",
            "ground_truth_action": ""
        }
        
        events.append({
            "event_id": generate_id("evt"),
            "entity_type": "subscription",
            "entity_id": sub["subscription_id"],
            "customer_id": sub["customer_id"],
            "event_type": "subscription.created",
            "amount": mrr,
            "currency": CURRENCY,
            "timestamp": created_at.isoformat(),
            "metadata": f'{{"plan": "{plan_id}"}}'
        })
        
        customer["customer_ltv"] += mrr * sub["paid_count"]
        
        if status in ["pending", "halted"]:
            pending_date = created_at + timedelta(days=sub["paid_count"]*30)
            if pending_date > datetime.now():
                pending_date = created_at + timedelta(seconds=random.randint(1, int((datetime.now() - created_at).total_seconds())))
            sub["pending_since"] = pending_date.isoformat()
            sub["auth_attempts"] = random.randint(1, 3)
            
            causes = [f for f in FAILURE_CAUSES if f[1] >= 0.05]
            cause_info = random.choice(causes)
            sub["failure_reason"] = cause_info[0]
            sub["recoverable"] = str(cause_info[2]).lower()
            sub["ground_truth_action"] = cause_info[3] if cause_info[2] else "ESCALATE"
            
            events.append({
                "event_id": generate_id("evt"),
                "entity_type": "subscription",
                "entity_id": sub["subscription_id"],
                "customer_id": sub["customer_id"],
                "event_type": "subscription.pending",
                "amount": mrr,
                "currency": CURRENCY,
                "timestamp": pending_date.isoformat(),
                "metadata": f'{{"reason": "{sub["failure_reason"]}"}}'
            })
            
            if status == "halted":
                halted_date = pending_date + timedelta(days=3)
                if halted_date > datetime.now():
                    halted_date = datetime.now()
                sub["halted_at"] = halted_date.isoformat()
                events.append({
                    "event_id": generate_id("evt"),
                    "entity_type": "subscription",
                    "entity_id": sub["subscription_id"],
                    "customer_id": sub["customer_id"],
                    "event_type": "subscription.halted",
                    "amount": mrr,
                    "currency": CURRENCY,
                    "timestamp": halted_date.isoformat(),
                    "metadata": "{}"
                })
                
        subscriptions.append(sub)
    return subscriptions

def generate_checkouts(customers, events):
    checkouts = []
    
    for i in range(NUM_CHECKOUTS):
        customer = random.choice(customers)
        cust_created = datetime.fromisoformat(customer["created_at"])
        created_at = random_date(cust_created, datetime.now())
        amount = random.choice(get_amount_choices())
        
        is_abandoned = random.random() < 0.4
        
        checkout = {
            "checkout_id": generate_id("chk"),
            "customer_id": customer["customer_id"],
            "amount": amount,
            "currency": CURRENCY,
            "payment_method": customer["default_payment_method"],
            "status": "abandoned" if is_abandoned else "completed",
            "created_at": created_at.isoformat(),
            "authorized_at": "",
            "abandoned_at": "",
            "abandonment_reason": "",
            "recoverable": ""
        }
        
        events.append({
            "event_id": generate_id("evt"),
            "entity_type": "checkout",
            "entity_id": checkout["checkout_id"],
            "customer_id": checkout["customer_id"],
            "event_type": "checkout.created",
            "amount": amount,
            "currency": CURRENCY,
            "timestamp": created_at.isoformat(),
            "metadata": "{}"
        })
        
        if is_abandoned:
            abandoned_at = created_at + timedelta(minutes=random.randint(5, 30))
            checkout["abandoned_at"] = abandoned_at.isoformat()
            checkout["abandonment_reason"] = "timeout"
            checkout["recoverable"] = "true"
            events.append({
                "event_id": generate_id("evt"),
                "entity_type": "checkout",
                "entity_id": checkout["checkout_id"],
                "customer_id": checkout["customer_id"],
                "event_type": "checkout.abandoned",
                "amount": amount,
                "currency": CURRENCY,
                "timestamp": abandoned_at.isoformat(),
                "metadata": "{}"
            })
        else:
            auth_at = created_at + timedelta(seconds=random.randint(30, 120))
            checkout["authorized_at"] = auth_at.isoformat()
            events.append({
                "event_id": generate_id("evt"),
                "entity_type": "checkout",
                "entity_id": checkout["checkout_id"],
                "customer_id": checkout["customer_id"],
                "event_type": "checkout.completed",
                "amount": amount,
                "currency": CURRENCY,
                "timestamp": auth_at.isoformat(),
                "metadata": "{}"
            })
            customer["customer_ltv"] += amount
            
        checkouts.append(checkout)
    return checkouts

def write_csv(filename, data):
    if not data:
        return
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def main():
    print("Generating synthetic dataset...")
    events = []
    
    customers = generate_customers()
    payments = generate_payments(customers, events)
    subscriptions = generate_subscriptions(customers, events)
    checkouts = generate_checkouts(customers, events)
    
    # Sort events by timestamp
    events.sort(key=lambda x: x["timestamp"])
    
    write_csv(f"{OUTPUT_DIR}/customers.csv", customers)
    write_csv(f"{OUTPUT_DIR}/payments.csv", payments)
    write_csv(f"{OUTPUT_DIR}/subscriptions.csv", subscriptions)
    write_csv(f"{OUTPUT_DIR}/checkout_sessions.csv", checkouts)
    write_csv(f"{OUTPUT_DIR}/payment_events.csv", events)
    
    # Summary calculation
    failed_payments = [p for p in payments if p["status"] == "failed"]
    recov_payments = [p for p in failed_payments if p["recoverable"] == "true"]
    unrecov_payments = [p for p in failed_payments if p["recoverable"] == "false"]
    
    sub_pending = [s for s in subscriptions if s["status"] == "pending"]
    sub_halted = [s for s in subscriptions if s["status"] == "halted"]
    
    chk_abandoned = [c for c in checkouts if c["status"] == "abandoned"]
    
    revenue_at_risk = sum(p["amount"] for p in failed_payments) + \
                      sum(s["mrr_value"] for s in sub_pending + sub_halted) + \
                      sum(c["amount"] for c in chk_abandoned)
                      
    print("========================================")
    print("Revenue Recovery Dataset")
    print("========================================")
    print(f"Customers:              {len(customers)}")
    print(f"Payments:               {len(payments)}")
    print(f"Subscriptions:          {len(subscriptions)}")
    print(f"Checkout Sessions:      {len(checkouts)}")
    print(f"Events:                 {len(events)}")
    print()
    print(f"Failed Payments:        {len(failed_payments)}")
    print(f"Recoverable:            {len(recov_payments)}")
    print(f"Unrecoverable:          {len(unrecov_payments)}")
    print()
    print(f"Subscription Pending:   {len(sub_pending)}")
    print(f"Subscription Halted:    {len(sub_halted)}")
    print()
    print(f"Checkout Abandoned:     {len(chk_abandoned)}")
    print()
    print(f"Total Revenue at Risk:  INR {revenue_at_risk}")
    print("========================================")

if __name__ == "__main__":
    main()
