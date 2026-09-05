from fastapi import FastAPI
from backend.app.api import health, webhooks, events, recovery, metrics, detection, intelligence
from backend.app.db.database import engine, Base
from backend.app.models import domain

# Create database tables
Base.metadata.create_all(bind=engine)

import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(
    title="Revenue Recovery Agent",
    description="Deterministic Phase 7 Buildathon Demo",
    version="1.0.0"
)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    # Add to request state for access in endpoints/loggers
    request.state.request_id = req_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP_ERROR", "message": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "VALIDATION_ERROR", "message": "Invalid request parameters", "details": exc.errors()}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Do not expose python stack traces
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."}
    )

app.include_router(health.router)
app.include_router(webhooks.router)
app.include_router(events.router)
app.include_router(recovery.router)
app.include_router(metrics.router)
app.include_router(detection.router)
app.include_router(intelligence.router)
