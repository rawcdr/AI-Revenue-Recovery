# Data Lineage and Leakage Protection

The integrity of the ML Feedback Loop relies on strictly controlling when data becomes available to the model.

## 1. Lineage Flow

**Raw Event (`Event`)**
- Input: JSON webhook payload from Razorpay simulation.
- Output: Validated and normalized SQLite `events` table row.

**Persistence (`Payment`, `Subscription`, `Customer`)**
- Input: Normalized event data.
- Output: Entity records in SQLite with current state (`failed`, `halted`, etc.).

**Recovery Candidate (`RecoveryCandidate`)**
- Input: Database polling of `payments` and `subscriptions` tables.
- Output: A materialized candidate with a deterministic priority score and an `ACTIVE` state.

**Features (`Inference`)**
- Input: Real-time query of candidate state (amount, retry count, customer segment).
- Output: A numerical vector mapped strictly by `feature-schema-v1`.
- **Constraint:** Features absolutely CANNOT contain final success/failure outcomes.

**Prediction (`RecoveryPrediction`)**
- Input: Feature vector pushed through the active registry model.
- Output: Probabilities and the selected action, stored immutably in `recovery_predictions`.

**Action (`RecoveryAction`)**
- Input: Recommended action + candidate state + policy validation.
- Output: An idempotent action request with state machine tracking (`PENDING → SUCCEEDED/FAILED/BLOCKED`).

**Outcome (`RecoveryOutcome`)**
- Input: The deterministic result of the execution simulator.
- Output: `RECOVERED`, `NOT_RECOVERED`, `ESCALATED`, or `BLOCKED` status in `recovery_outcomes`.

**Feedback (`RecoveryFeedback`)**
- Input: Chronological join of Candidate → Prediction → Action → Outcome.
- Output: Flat ledger used for drift analysis and future training.

## 2. Inference-Time Features vs. Historical Outcome Labels

This distinction is critical for preventing target leakage.

### Inference-Time Features (USED by the model at prediction time)

| Feature | Source | Available At |
|---|---|---|
| `customer_segment` | `Customer` table | Before prediction |
| `payment_method` | `Payment` table | Before prediction |
| `error_code` | `Payment` table | Before prediction |
| `amount_relative` | `RecoveryCandidate` | Before prediction |
| `retry_count` | `RecoveryCandidate` | Before prediction |
| `hour` | `RecoveryCandidate.detected_at` | Before prediction |
| `day_of_week` | `RecoveryCandidate.detected_at` | Before prediction |
| `hist_payment_count` | Historical aggregation | Before prediction |
| `hist_success_rate` | Historical aggregation | Before prediction |

### Historical Outcome Labels (NEVER available at prediction time)

| Label | Source | Available At |
|---|---|---|
| `actual_outcome` | `RecoveryOutcome` | **After** execution |
| `recovered_amount` | `RecoveryOutcome` | **After** execution |
| `failure_reason` | `RecoveryOutcome` | **After** execution |
| `action_result` | `RecoveryAction` | **After** execution |

## 3. Target Leakage Protection

- **Physical Separation:** The ground-truth outcome label (`actual_outcome`, `recovered_amount`) is structurally isolated in the `RecoveryOutcome` and `RecoveryFeedback` schemas. It is impossible for `score_candidate()` to query these fields during inference because they do not exist until *after* the orchestrator completes execution.
- **Chronological Feedback:** The `build_feedback_dataset.py` script enforces a strict chronological join, guaranteeing that the model only evaluates historical actions against their subsequent finalized outcomes.
- **Schema Enforcement:** The feature extraction function `build_inference_features()` explicitly constructs only the fields listed in the inference-time table above. It does not query `RecoveryOutcome` or `RecoveryFeedback`.
