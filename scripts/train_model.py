import os
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, brier_score_loss
import warnings

# Suppress sklearn warnings for cleaner output
warnings.filterwarnings('ignore')

from backend.app.intelligence.features import build_preprocessor, get_feature_schema
from backend.app.intelligence.registry import save_models

def train_and_select(X_train, y_train, X_val, y_val, action_name):
    print(f"\nTraining models for: {action_name}")
    
    # 1. Baseline Logistic Regression
    lr = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
    calibrated_lr = CalibratedClassifierCV(lr, method='sigmoid', cv=3)
    calibrated_lr.fit(X_train, y_train)
    
    y_val_prob_lr = calibrated_lr.predict_proba(X_val)[:, 1]
    roc_lr = roc_auc_score(y_val, y_val_prob_lr)
    brier_lr = brier_score_loss(y_val, y_val_prob_lr)
    
    print(f"  Logistic Regression - ROC-AUC: {roc_lr:.4f}, Brier: {brier_lr:.4f}")
    
    # 2. Random Forest
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, class_weight='balanced', random_state=42)
    calibrated_rf = CalibratedClassifierCV(rf, method='isotonic', cv=3)
    calibrated_rf.fit(X_train, y_train)
    
    y_val_prob_rf = calibrated_rf.predict_proba(X_val)[:, 1]
    roc_rf = roc_auc_score(y_val, y_val_prob_rf)
    brier_rf = brier_score_loss(y_val, y_val_prob_rf)
    
    print(f"  Random Forest       - ROC-AUC: {roc_rf:.4f}, Brier: {brier_rf:.4f}")
    
    # Select best based on Brier score (lower is better calibrated)
    if brier_rf <= brier_lr:
        print(f"  -> Selected: Random Forest")
        return calibrated_rf, roc_rf, brier_rf
    else:
        print(f"  -> Selected: Logistic Regression")
        return calibrated_lr, roc_lr, brier_lr

def main():
    data_path = 'data/training/recovery_training_data.csv'
    if not os.path.exists(data_path):
        print(f"Training data not found at {data_path}. Run generate_training_data.py first.")
        return
        
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} rows.")
    
    categorical, numerical = get_feature_schema()
    features = categorical + numerical
    
    # 70/15/15 split using GroupShuffleSplit on customer_id
    # First split: 70% Train, 30% Temp (Val + Test)
    gss1 = GroupShuffleSplit(n_splits=1, train_size=0.7, random_state=42)
    train_idx, temp_idx = next(gss1.split(df, groups=df['customer_id']))
    
    train_df = df.iloc[train_idx]
    temp_df = df.iloc[temp_idx]
    
    # Second split: 50% of Temp = 15% Val, 50% of Temp = 15% Test
    gss2 = GroupShuffleSplit(n_splits=1, train_size=0.5, random_state=42)
    val_idx, test_idx = next(gss2.split(temp_df, groups=temp_df['customer_id']))
    
    val_df = temp_df.iloc[val_idx]
    test_df = temp_df.iloc[test_idx]
    
    print(f"Split sizes -> Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    # Leakage check: Verify no overlapping customers
    train_customers = set(train_df['customer_id'])
    val_customers = set(val_df['customer_id'])
    test_customers = set(test_df['customer_id'])
    
    assert len(train_customers.intersection(val_customers)) == 0, "Leakage: Train and Val customers overlap!"
    assert len(train_customers.intersection(test_customers)) == 0, "Leakage: Train and Test customers overlap!"
    assert len(val_customers.intersection(test_customers)) == 0, "Leakage: Val and Test customers overlap!"
    
    # Preprocessing
    preprocessor = build_preprocessor()
    X_train = preprocessor.fit_transform(train_df[features])
    X_val = preprocessor.transform(val_df[features])
    
    y_train_retry = train_df['retry_success']
    y_val_retry = val_df['retry_success']
    
    y_train_update = train_df['payment_update_success']
    y_val_update = val_df['payment_update_success']
    
    retry_model, _, _ = train_and_select(X_train, y_train_retry, X_val, y_val_retry, "RETRY")
    update_model, _, _ = train_and_select(X_train, y_train_update, X_val, y_val_update, "PAYMENT_UPDATE")
    
    # Save the selected models
    metadata = {
        "model_version": "recovery-model-v1",
        "feature_version": "feature-schema-v1",
        "training_data_version": "training-data-v1",
        "description": "Local Tabular ML models for Recovery Predictions"
    }
    
    save_models(metadata, preprocessor, retry_model, update_model)
    print("\nModels successfully saved to models/recovery_intelligence.joblib")
    
    # Save test dataset for evaluate_model.py
    test_df.to_csv('data/training/test_data.csv', index=False)
    print("Saved test data to data/training/test_data.csv")

if __name__ == "__main__":
    main()
