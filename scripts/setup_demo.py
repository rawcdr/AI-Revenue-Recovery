import os
import sys
import subprocess

# Add project root to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.database import SessionLocal
from backend.app.models.domain import ModelRegistry, Payment, RecoveryCandidate
from backend.app.services.registry import promote_model

def run_command(cmd_list, desc):
    print(f"\n========================================")
    print(f"{desc}")
    print(f"========================================")
    result = subprocess.run(cmd_list)
    if result.returncode != 0:
        print(f"FAILED: {desc}")
        sys.exit(1)

def setup_demo():
    print("Starting AI Revenue Recovery Demo Setup...\n")
    
    # 1. Reset Database and Seed Synthetic Data
    run_command([sys.executable, "scripts/seed_database.py", "--reset"], "Seeding Database")
    
    # 2. Register and Promote the Model
    print("\n========================================")
    print("Initializing Model Registry")
    print("========================================")
    db = SessionLocal()
    
    # Check if model exists, if not create a mock one
    model_version = "recovery-v2"
    existing = db.query(ModelRegistry).filter_by(model_version=model_version).first()
    if not existing:
        print(f"Registering model {model_version} as VALIDATED.")
        m = ModelRegistry(
            version_id="v2", 
            model_version=model_version, 
            model_type="sklearn", 
            feature_version="feature-schema-v1", 
            status="VALIDATED", 
            training_timestamp="2026-09-01T00:00:00",
            validation_roc_auc=0.85,
            test_roc_auc=0.84
        )
        db.add(m)
        db.commit()
    else:
        print(f"Model {model_version} already registered.")
        
    promote_model(db, model_version)
    print(f"SUCCESS: Model {model_version} has been explicitly promoted to ACTIVE.")
    
    # 3. Run Detection to populate RecoveryCandidates
    run_command([sys.executable, "scripts/run_detection.py"], "Running Candidate Detection")
    
    # 4. Prepare Deterministic Demo Scenarios
    print("\n========================================")
    print("Preparing Deterministic Demo Scenarios")
    print("========================================")
    
    # We will pick 3 specific payments and force their state to guarantee the demo
    # SCENARIO A: network_error -> RETRY
    # SCENARIO B: expired_card -> PAYMENT_UPDATE
    # SCENARIO C: suspected_fraud -> POLICY BLOCK
    
    # Find candidates to hijack for the demo
    candidates = db.query(RecoveryCandidate).filter_by(status="ACTIVE").limit(3).all()
    
    if len(candidates) == 3:
        # Hijack candidate 0 (Scenario A)
        c0 = candidates[0]
        p0 = db.query(Payment).filter_by(payment_id=c0.entity_id).first()
        if p0:
            p0.error_code = "network_error"
            p0.amount = 1200.0
            
        # Hijack candidate 1 (Scenario B)
        c1 = candidates[1]
        p1 = db.query(Payment).filter_by(payment_id=c1.entity_id).first()
        if p1:
            p1.error_code = "expired_card"
            p1.amount = 2500.0
            
        # Hijack candidate 2 (Scenario C)
        c2 = candidates[2]
        p2 = db.query(Payment).filter_by(payment_id=c2.entity_id).first()
        if p2:
            p2.error_code = "suspected_fraud"
            p2.amount = 50000.0
            
        db.commit()
        
        print(f"Demo Scenarios Prepared:")
        print(f" - SCENARIO A (Network Error -> RETRY): Candidate ID: {c0.candidate_id}")
        print(f" - SCENARIO B (Expired Card -> UPDATE): Candidate ID: {c1.candidate_id}")
        print(f" - SCENARIO C (Fraud -> ESCALATE): Candidate ID: {c2.candidate_id}")
        
    else:
        print("WARNING: Could not find 3 candidates to mock scenarios.")
    
    db.close()
    
    # 5. Build Feedback Dataset
    run_command([sys.executable, "scripts/build_feedback_dataset.py"], "Building Feedback Ledger")
    
    print("\n========================================")
    print("Demo Setup Complete!")
    print("========================================")
    print("You can now run the backend:")
    print("uvicorn backend.app.main:app --reload")

if __name__ == "__main__":
    setup_demo()
