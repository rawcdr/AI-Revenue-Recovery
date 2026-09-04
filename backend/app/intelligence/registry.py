import os
import joblib

MODEL_DIR = "models"
MODEL_FILE = os.path.join(MODEL_DIR, "recovery_intelligence.joblib")

def save_models(metadata, preprocessor, retry_model, update_model):
    os.makedirs(MODEL_DIR, exist_ok=True)
    payload = {
        "metadata": metadata,
        "preprocessor": preprocessor,
        "retry_model": retry_model,
        "update_model": update_model
    }
    joblib.dump(payload, MODEL_FILE)
    
def load_models():
    if not os.path.exists(MODEL_FILE):
        return None
    return joblib.load(MODEL_FILE)
