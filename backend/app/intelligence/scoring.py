from typing import Dict, Any, Tuple

def score_predictions(amount: float, probabilities: Dict[str, float]) -> Tuple[str, float]:
    """
    Returns (recommended_action, expected_recovery_value)
    """
    retry = probabilities.get("retry_probability", 0.0)
    update = probabilities.get("payment_update_probability", 0.0)
    escalate = probabilities.get("escalation_probability", 0.0)
    
    # Identify the highest probability
    best_action = "ESCALATE"
    best_prob = escalate
    
    if retry > best_prob:
        best_prob = retry
        best_action = "RETRY"
        
    if update > best_prob:
        best_prob = update
        best_action = "PAYMENT_UPDATE"
        
    expected_value = amount * best_prob
    
    return best_action, expected_value
