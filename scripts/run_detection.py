import sys
import os

# Add project root to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.database import SessionLocal
from backend.app.services.detection import run_detection

def main():
    db = SessionLocal()
    try:
        stats = run_detection(db)
        print("========================================")
        print("Detection Run")
        print("========================================")
        print(f"Candidates detected:       {stats['active_candidates']}")
        print(f"New candidates:             {stats['new_candidates']}")
        print(f"Updated candidates:        {stats['updated_candidates']}")
        print(f"Resolved candidates:        {stats['resolved_candidates']}\n")
        print(f"Revenue at risk:        INR {stats['revenue_at_risk']}")
        print("========================================")
    finally:
        db.close()

if __name__ == "__main__":
    main()
