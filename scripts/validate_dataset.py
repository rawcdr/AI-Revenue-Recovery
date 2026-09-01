import csv
import os
from datetime import datetime

DATA_DIR = "data/generated"

def validate_files_exist():
    files = ["customers.csv", "payments.csv", "subscriptions.csv", "checkout_sessions.csv", "payment_events.csv"]
    for f in files:
        if not os.path.exists(os.path.join(DATA_DIR, f)):
            print(f"FAIL: File {f} missing.")
            return False
    return True

def read_csv(filename):
    with open(os.path.join(DATA_DIR, filename), "r", encoding='utf-8') as f:
        return list(csv.DictReader(f))

def validate():
    if not validate_files_exist():
        return False
        
    customers = read_csv("customers.csv")
    payments = read_csv("payments.csv")
    subscriptions = read_csv("subscriptions.csv")
    checkouts = read_csv("checkout_sessions.csv")
    events = read_csv("payment_events.csv")
    
    passed = True
    
    # 1. Row counts
    if len(customers) < 200: passed = False; print("FAIL: Customers count < 200")
    if len(payments) < 300: passed = False; print("FAIL: Payments count < 300")
    if len(subscriptions) < 100: passed = False; print("FAIL: Subscriptions count < 100")
    if len(checkouts) < 150: passed = False; print("FAIL: Checkouts count < 150")
    if len(events) < 100: passed = False; print("FAIL: Events count < 100")
    
    # 2. Referential integrity
    customer_ids = {c["customer_id"] for c in customers}
    
    for p in payments:
        if p["customer_id"] not in customer_ids:
            passed = False; print(f"FAIL: Invalid customer_id in payment {p['payment_id']}")
    for s in subscriptions:
        if s["customer_id"] not in customer_ids:
            passed = False; print(f"FAIL: Invalid customer_id in sub {s['subscription_id']}")
    for c in checkouts:
        if c["customer_id"] not in customer_ids:
            passed = False; print(f"FAIL: Invalid customer_id in checkout {c['checkout_id']}")
    for e in events:
        if e["customer_id"] not in customer_ids:
            passed = False; print(f"FAIL: Invalid customer_id in event {e['event_id']}")
            
    # 3. Amount and currency
    for p in payments:
        if float(p["amount"]) <= 0: passed = False; print("FAIL: Amount <= 0 in payments")
        if p["currency"] != "INR": passed = False; print("FAIL: Currency != INR in payments")
    for s in subscriptions:
        if float(s["mrr_value"]) <= 0: passed = False; print("FAIL: mrr_value <= 0 in subs")
        if s["currency"] != "INR": passed = False; print("FAIL: Currency != INR in subs")
    for c in checkouts:
        if float(c["amount"]) <= 0: passed = False; print("FAIL: amount <= 0 in checkouts")
        if c["currency"] != "INR": passed = False; print("FAIL: Currency != INR in checkouts")
        
    # 4. Temporal consistency
    for p in payments:
        if p["failed_at"]:
            if datetime.fromisoformat(p["created_at"]) > datetime.fromisoformat(p["failed_at"]):
                passed = False; print("FAIL: created_at > failed_at in payment")
    for s in subscriptions:
        if s["pending_since"]:
            if datetime.fromisoformat(s["created_at"]) > datetime.fromisoformat(s["pending_since"]):
                passed = False; print("FAIL: created_at > pending_since in sub")
        if s["halted_at"] and s["pending_since"]:
            if datetime.fromisoformat(s["pending_since"]) > datetime.fromisoformat(s["halted_at"]):
                passed = False; print("FAIL: pending_since > halted_at in sub")
                
    # 5. Ground truth validity
    valid_actions = {"RETRY", "PAYMENT_UPDATE", "ESCALATE"}
    for p in payments:
        if p["status"] == "failed":
            if p["recoverable"] not in {"true", "false"}:
                passed = False; print("FAIL: invalid recoverable flag in payment")
            if p["ground_truth_action"] not in valid_actions:
                passed = False; print(f"FAIL: invalid action {p['ground_truth_action']} in payment")
                
    # 6. Event consistency check (sampled)
    # Check if a halted sub has a pending event
    sub_events = {}
    for e in events:
        if e["entity_type"] == "subscription":
            sub_events.setdefault(e["entity_id"], set()).add(e["event_type"])
            
    for s in subscriptions:
        if s["status"] == "halted":
            evts = sub_events.get(s["subscription_id"], set())
            if "subscription.pending" not in evts:
                passed = False; print("FAIL: Halted sub missing pending event")
                
    if passed:
        print("SUCCESS: All dataset validations passed.")
    else:
        print("VALIDATION FAILED.")
        
    return passed

if __name__ == "__main__":
    if not validate():
        exit(1)
