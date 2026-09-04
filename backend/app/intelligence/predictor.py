import pandas as pd
from typing import Dict, Any
from backend.app.intelligence.registry import load_models

class RecoveryPredictor:
    def __init__(self):
        models = load_models()
        if not models:
            raise RuntimeError("Models not found. Please run scripts/train_model.py first.")
            
        self.preprocessor = models['preprocessor']
        self.retry_model = models['retry_model']
        self.update_model = models['update_model']
        
    def predict(self, candidate_features: Dict[str, Any]) -> Dict[str, float]:
        df = pd.DataFrame([candidate_features])
        
        # Apply preprocessor
        X = self.preprocessor.transform(df)
        
        # Get probabilities
        retry_prob = float(self.retry_model.predict_proba(X)[0][1])
        update_prob = float(self.update_model.predict_proba(X)[0][1])
        
        # Calculate escalation probability
        # Escalate is generally inversely proportional to the maximum recovery probability
        # Or we explicitly model it. Since we only trained two models, we can infer it.
        # If both retry and update are low, escalate is high.
        escalate_prob = 1.0 - max(retry_prob, update_prob)
        
        return {
            "retry_probability": max(0.0, min(1.0, retry_prob)),
            "payment_update_probability": max(0.0, min(1.0, update_prob)),
            "escalation_probability": max(0.0, min(1.0, escalate_prob))
        }
