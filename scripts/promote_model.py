import os
import sys
import argparse

# Add the project root to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.database import SessionLocal
from backend.app.services.registry import promote_model

def main():
    parser = argparse.ArgumentParser(description="Explicitly promote a model version to ACTIVE")
    parser.add_argument("--version", type=str, required=True, help="Model version to promote (e.g., recovery-v2)")
    
    args = parser.parse_args()
    
    print(f"Attempting to promote model version: {args.version}")
    
    db = SessionLocal()
    try:
        promote_model(db, args.version)
        print(f"SUCCESS: Model {args.version} has been explicitly promoted to ACTIVE.")
        print("The previous ACTIVE model (if any) has been RETIRED.")
    except Exception as e:
        print(f"FAILED: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
