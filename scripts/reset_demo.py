import os
import sys

# Add project root to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.database import engine, Base

def reset_demo():
    print("Resetting AI Revenue Recovery Demo Environment...\n")
    
    # Drop all database tables
    print("Dropping database tables...")
    Base.metadata.drop_all(bind=engine)
    print("Database tables dropped successfully.")
    
    # Remove feedback dataset if exists
    feedback_file = "data/feedback/recovery_feedback.csv"
    if os.path.exists(feedback_file):
        os.remove(feedback_file)
        print(f"Removed generated file: {feedback_file}")
    
    # Remove generated SQLite DB file to be completely sure
    db_file = "recovery.db"
    if os.path.exists(db_file):
        # Disconnect engine to release file lock if any
        engine.dispose()
        try:
            os.remove(db_file)
            print(f"Removed database file: {db_file}")
        except Exception as e:
            print(f"Warning: Could not remove {db_file} (may be locked by another process). Error: {e}")
    
    print("\nEnvironment successfully reset to a clean state.")
    print("Run `python scripts/setup_demo.py` to rebuild it.")

if __name__ == "__main__":
    reset_demo()
