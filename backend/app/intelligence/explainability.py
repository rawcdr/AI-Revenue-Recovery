from typing import Dict, Any

def generate_explanation(recommended_action: str, candidate_features: Dict[str, Any]) -> str:
    """
    Generate a deterministic explanation derived from the input features and the action selected.
    In a real implementation this might use feature importance or SHAP values.
    Here we construct a rule-based mapping showing the strongest signal alignments.
    """
    signals = []
    
    # Analyze history
    if candidate_features.get('hist_success_rate', 0) > 0.7:
        signals.append("Customer historical success rate is high.")
    elif candidate_features.get('hist_payment_count', 0) == 0:
        signals.append("Customer has no payment history (new user).")
        
    # Analyze error codes
    error = candidate_features.get('error_code', '')
    if error == 'insufficient_funds':
        signals.append("Failure type 'insufficient_funds' is highly compatible with retry attempts.")
    elif error == 'expired_card':
        signals.append("Failure type 'expired_card' requires a payment update to proceed.")
    elif error in ['customer_dispute', 'suspected_fraud']:
        signals.append(f"Failure type '{error}' strongly prohibits automated recovery.")
        
    # Analyze retries
    retries = candidate_features.get('retry_count', 0)
    if retries == 0:
        signals.append("This is the first recovery attempt.")
    elif retries >= 3:
        signals.append("Maximum safe automated retry threshold reached.")
        
    base_text = f"Recommended Action: {recommended_action}\nSignals:\n"
    if not signals:
        return base_text + "- General model inference based on complex interactions."
        
    return base_text + "\n".join([f"- {s}" for s in signals])
