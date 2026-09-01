import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# We default to recovery.db if DATABASE_URL is not set or uses sqlite:///./recovery.db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recovery.db")

# For SQLite we need connect_args={"check_same_thread": False}
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
