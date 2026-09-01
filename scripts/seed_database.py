import csv
import argparse
import os
import sys

# Add project root to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.database import SessionLocal, engine, Base
from backend.app.models.domain import Customer, Payment, Subscription, Event

DATA_DIR = "data/generated"

def seed_database(reset=False):
    if reset:
        print("Resetting database...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Generic seeder
    def load_csv(filename, model, pk_field):
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            print(f"Skipping {filename} - file not found.")
            return
            
        with open(filepath, "r", encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = list(reader)
            
        added = 0
        for row in records:
            # Handle empty strings mapping to None for nullable fields
            cleaned_row = {k: (None if v == "" else v) for k, v in row.items()}
            
            # Idempotency check
            pk_val = cleaned_row[pk_field]
            exists = db.query(model).filter(getattr(model, pk_field) == pk_val).first()
            if not exists:
                if filename == 'payment_events.csv':
                    cleaned_row['metadata_'] = cleaned_row.pop('metadata')
                    cleaned_row['received_at'] = cleaned_row['timestamp']
                    
                obj = model(**cleaned_row)
                db.add(obj)
                added += 1
                
        db.commit()
        print(f"Seeded {added} new records into {model.__tablename__}.")

    load_csv("customers.csv", Customer, "customer_id")
    load_csv("payments.csv", Payment, "payment_id")
    load_csv("subscriptions.csv", Subscription, "subscription_id")
    load_csv("payment_events.csv", Event, "event_id")
    
    # We don't seed checkout_sessions as we haven't created a model for it yet, since it's out of scope for recovery queue right now.
    
    db.close()
    print("Seeding complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset database before seeding")
    args = parser.parse_args()
    seed_database(reset=args.reset)
