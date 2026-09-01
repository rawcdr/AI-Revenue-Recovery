from fastapi import FastAPI
from backend.app.api import health, webhooks, events, recovery, metrics, detection
from backend.app.db.database import engine, Base
from backend.app.models import domain

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Revenue Recovery Agent")

app.include_router(health.router)
app.include_router(webhooks.router)
app.include_router(events.router)
app.include_router(recovery.router)
app.include_router(metrics.router)
app.include_router(detection.router)
