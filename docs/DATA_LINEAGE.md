# Data Lineage and Leakage Protection

The integrity of the ML Feedback Loop relies on strictly controlling when data becomes available to the model.

## 1. Lineage Flow

**Raw Event (`Event`)**
- Input: JSON webhook payload from Razorpay simulation.
- Output: Validated and normalized SQLite `events` table row.

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
- Input: Recommended action + candidate state.
- Output: An idempotent action request (`PENDING`).

**Outcome (`RecoveryOutcome`)**
- Input: The deterministic result of the execution simulator.
- Output: `SUCCEEDED`, `FAILED`, or `BLOCKED` status in `recovery_outcomes`.

**Feedback (`RecoveryFeedback`)**
- Input: Chronological join of Candidate -> Prediction -> Action -> Outcome.
- Output: Flat ledger used for drift analysis and future training.

## 2. Target Leakage Protection

- **Physical Separation:** The ground-truth outcome label (`actual_outcome`, `recovered_amount`) is structurally isolated in the `RecoveryOutcome` and `RecoveryFeedback` schemas. It is impossible for `score_candidate()` to query these fields during inference because they do not exist until *after* the orchestrator completes execution.
- **Chronological Feedback:** The `build_feedback_dataset.py` script enforces a strict chronological join, guaranteeing that the model only evaluates historical actions against their subsequent finalized outcomes.
