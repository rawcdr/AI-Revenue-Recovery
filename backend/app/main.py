from fastapi import FastAPI

app = FastAPI(title="Revenue Recovery Agent")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "revenue-recovery-agent"
    }
