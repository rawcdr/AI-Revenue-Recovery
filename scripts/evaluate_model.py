import os
import pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss, classification_report

from backend.app.intelligence.registry import load_models
from backend.app.intelligence.features import get_feature_schema

def evaluate_action(y_true, y_prob, action_name):
    print(f"\n--- {action_name} Metrics ---")
    roc = roc_auc_score(y_true, y_prob)
    brier = brier_score_loss(y_true, y_prob)
    
    # Threshold at 0.5 for precision/recall
    y_pred = (y_prob >= 0.5).astype(int)
    print(f"ROC-AUC: {roc:.4f}")
    print(f"Brier Score (Calibration): {brier:.4f}")
    print(classification_report(y_true, y_pred))

def main():
    test_data_path = 'data/training/test_data.csv'
    if not os.path.exists(test_data_path):
        print("Test data not found. Run train_model.py first.")
        return
        
    models = load_models()
    if not models:
        print("Models not found. Run train_model.py first.")
        return
        
    df = pd.read_csv(test_data_path)
    print(f"Loaded {len(df)} test records.")
    
    preprocessor = models['preprocessor']
    retry_model = models['retry_model']
    update_model = models['update_model']
    
    categorical, numerical = get_feature_schema()
    features = categorical + numerical
    
    X_test = preprocessor.transform(df[features])
    
    # Evaluate Retry
    y_test_retry = df['retry_success']
    y_prob_retry = retry_model.predict_proba(X_test)[:, 1]
    evaluate_action(y_test_retry, y_prob_retry, "RETRY")
    
    # Evaluate Payment Update
    y_test_update = df['payment_update_success']
    y_prob_update = update_model.predict_proba(X_test)[:, 1]
    evaluate_action(y_test_update, y_prob_update, "PAYMENT_UPDATE")
    
    # Business Metrics Evaluation
    # For every test record, compute recommended action and expected value
    
    print("\n--- Business/Recommendation Metrics (Synthetic) ---")
    total_amount = df['amount'].sum()
    total_expected_recovery = 0.0
    correct_recommendations = 0
    
    for i in range(len(df)):
        row = df.iloc[i]
        amount = row['amount']
        
        p_retry = y_prob_retry[i]
        p_update = y_prob_update[i]
        p_escalate = 1.0 - max(p_retry, p_update)
        
        probs = {"RETRY": p_retry, "PAYMENT_UPDATE": p_update, "ESCALATE": p_escalate}
        best_action = max(probs, key=probs.get)
        
        expected_value = amount * probs[best_action]
        total_expected_recovery += expected_value
        
        # Check if recommendation was actually successful in the synthetic truth
        # For Escalate, we assume it's "correct" if both retry and update failed.
        if best_action == "RETRY" and row['retry_success'] == 1:
            correct_recommendations += 1
        elif best_action == "PAYMENT_UPDATE" and row['payment_update_success'] == 1:
            correct_recommendations += 1
        elif best_action == "ESCALATE" and row['retry_success'] == 0 and row['payment_update_success'] == 0:
            correct_recommendations += 1
            
    rec_accuracy = correct_recommendations / len(df)
    recovery_rate = total_expected_recovery / total_amount if total_amount > 0 else 0
    
    print(f"Recommendation Accuracy: {rec_accuracy:.2%}")
    print(f"Total Amount at Risk: {total_amount:,.2f}")
    print(f"Predicted Total Expected Recovery: {total_expected_recovery:,.2f}")
    print(f"Revenue-Weighted Recovery Rate: {recovery_rate:.2%}")
    
if __name__ == "__main__":
    main()
