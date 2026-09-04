# Phase 4: Custom Recovery Intelligence Engine

This phase introduces an entirely local, tabular ML-based intelligence engine designed to predict the optimal recovery action (`RETRY`, `PAYMENT_UPDATE`, `ESCALATE`) and maximize Expected Recovery Value.

## CRITICAL BOUNDARY
**No external Foundation Models (Claude/GPT/Gemini) are used in this architecture.**
This ensures data privacy, predictability, zero marginal inference cost, and millisecond latency. 

Furthermore, this engine purely **predicts probabilities**. It strictly **does not execute retries or communicate with customers**. Execution and policy governance are reserved for Phase 5.

## Training Data & Simulation
Since the Phase 1 dataset lacks historical outcomes (which are required for supervised learning), we generate 20,000 rows of synthetic, probabilistically deterministic training data (`scripts/generate_training_data.py`).

The simulator avoids generic random assignment. It injects logical biases:
- `insufficient_funds` combined with high historical success heavily favors `RETRY` success.
- `expired_card` heavily penalizes `RETRY` and favors `PAYMENT_UPDATE`.
- `customer_dispute` suppresses both, steering the engine toward `ESCALATE`.

### Target Leakage Prevention
Features include *only* data available at detection time (e.g., historical success rates, failure code, amount, temporal factors). Post-recovery outcomes or true ground-truth targets are explicitly omitted from the feature matrix.

## Model Architecture
The engine is split across independent models optimized for each action space:
1. `RetryModel` (Predicts `P(success | action=RETRY)`)
2. `PaymentUpdateModel` (Predicts `P(success | action=PAYMENT_UPDATE)`)

The pipeline evaluates both a Baseline (`LogisticRegression`) and a Stronger Tabular Model (`RandomForestClassifier`), selecting the champion based on Brier Score to ensure well-calibrated probabilities.

*Note: `ESCALATE` probability is inferred indirectly based on the inverse of the maximum automated recovery probability.*

### Feature Engineering (`backend/app/intelligence/features.py`)
- **Numerical Features**: Standardized via `StandardScaler`. Includes amount, hour, day of week, retry count, and historical rates.
- **Categorical Features**: Encoded via `OneHotEncoder`. Includes customer segment, payment method, and failure type.

## Evaluation & Calibration
Models are evaluated on a 70/15/15 Train/Val/Test split.
To prevent behavioral leakage, the dataset is split using `GroupShuffleSplit` on `customer_id` ensuring a single customer is exclusively confined to either train, validation, or test.

Evaluated metrics:
- ROC-AUC
- Brier Score (Calibration quality)
- Expected Recovery Value (`amount × selected_probability`)
- Recommendation Accuracy

## Persistence
Models, preprocessors, and metadata are serialized via `joblib` into `models/recovery_intelligence.joblib`. 
This guarantees the exact transformation rules applied during training are identically replicated during API inference.

## API Integration
The inference engine exposes:
- `POST /intelligence/run`: Batch score un-scored active candidates (limited by `INTELLIGENCE_MAX_BATCH`).
- `POST /intelligence/{candidate_id}`: Score a specific candidate on-demand.
- `GET /intelligence/{candidate_id}`: Fetch the latest stored prediction and AI explanation.
