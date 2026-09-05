# Phase 6: Recovery Feedback, Model Evaluation, and Explicit Promotion

Phase 6 closes the loop on our machine learning architecture by establishing a robust feedback framework, a secure model registry, drift monitoring, and a lightweight dashboard. Crucially, this architecture retains absolute deterministic control over model promotion and retraining.

## Feedback Architecture & Data Lineage
The system captures the entire lifecycle of a recovery attempt:
1. `RecoveryCandidate` (the core entity at risk)
2. `RecoveryPrediction` (the ML recommendation generated at inference time)
3. `RecoveryAction` (the actual executed action, influenced by policy limits)
4. `RecoveryOutcome` (the realized outcome and recovered revenue)

The `scripts/build_feedback_dataset.py` joins these tables to generate `RecoveryFeedback`, serving as a materialized historical ledger, and exports this to `data/feedback/recovery_feedback.csv`.

## Leakage Protection
To prevent target leakage:
- The historical outcome fields (`actual_outcome`, `recovered_amount`) strictly reside in the `RecoveryFeedback` and `RecoveryOutcome` entities.
- These target labels are physically disconnected from the `RecoveryPrediction` schema.
- Inference-time features cannot accidentally ingest future outcomes.

## Evaluation Metrics
### Action Performance
Evaluated across `RETRY`, `PAYMENT_UPDATE`, and `ESCALATE`. Tracks raw counts, successful executions, realized recoveries, and total revenue recovered.
### Calibration
Predictions are bucketed by probability (e.g., 0.0-0.2, 0.8-1.0). The average predicted probability is compared against the actual realized recovery rate per bucket.
### Revenue-Weighted Evaluation
Ensures that we track absolute expected vs. realized revenue. Crucially, the logic aggressively deduplicates by `candidate_id` to prevent double-counting revenue if an anomaly triggers dual recoveries.

## Model Registry & Promotion
Models are tracked in the `ModelRegistry` table with states: `TRAINED`, `VALIDATED`, `ACTIVE`, and `RETIRED`.
- Only **one** model version can be `ACTIVE` at any given time.
- **Explicit Promotion:** Model promotion is NOT automatic. It is explicitly executed via `scripts/promote_model.py --version <version>`. The script strictly verifies that the model is `VALIDATED` before shifting the currently `ACTIVE` model to `RETIRED`.

## Drift Detection & Retraining Recommendation
- Drift detection evaluates historical data in the feedback ledger. 
- It chronologically compares category distributions and aggregate performance (e.g. tracking a 15% absolute degradation in recovery rate).
- **Retraining Recommendation:** Outputs `RETRAIN_RECOMMENDED` or `NO_RETRAINING_REQUIRED`. It does NOT automatically trigger a retraining pipeline.

## Dashboard & APIs
- **APIs:** Fast API exposes `GET /metrics/feedback`, `GET /intelligence/models`, `GET /intelligence/performance`, and `GET /intelligence/drift`.
- **Dashboard:** A vanilla HTML/JS `frontend/index.html` UI beautifully renders revenue at risk, action metrics, calibration tables, and current drift states without housing any internal business logic.

## Safety Boundaries
- **No Automatic Retraining:** Recommendations only.
- **No Automatic Promotion:** Scripted, manual CLI gate only.
- **No Real Execution:** Remains bound strictly to deterministic logic.
- **No External AI:** Complete absence of OpenAI, Claude, or Anthropic traces confirmed.

## Testing
`backend/tests/test_phase6.py` verifies:
- Target leakage schemas
- Feedback creation and revenue deduplication
- Calibration logic
- Drift thresholds
- Registry single-active constraints
- Valid / invalid model promotion logic
