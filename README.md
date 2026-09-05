# AI Revenue Recovery Agent

A fully bounded, deterministic, tabular-ML-driven orchestrator designed to intelligently recover failed payments and halted subscriptions for the Razorpay Buildathon.

---

> **Synthetic Data Disclaimer:** The dataset is entirely synthetic. No real PII or payment data is used. The ML metrics are based on synthetic data and should not be interpreted as production performance.

> **Simulated Payment Disclaimer:** Payment execution is **simulated**. The system does not possess real payment credentials and cannot capture actual funds. `PAYMENT_EXECUTION_MODE` is enforced as `Literal["SIMULATED"]` at the type level.

> **No External AI Disclaimer:** No external LLM or foundation model is used. This system does **not** use Claude, OpenAI, Gemini, Anthropic, Hugging Face Inference, or any hosted AI service. All predictions are generated locally using scikit-learn.

---

## 1. Problem

Failed payments and halted subscriptions lead to massive involuntary churn for merchants. Recovering these payments blindly via brute-force retries incurs high network costs, triggers fraud flags, and alienates customers. Merchants need an intelligent system that identifies **which** payments can be recovered, **how** to recover them, and **when** to stop trying.

## 2. Solution

An intelligent, closed-loop recovery orchestrator that:

1. **Detects** failed payments and halted subscriptions from webhook events.
2. **Predicts** the probability of success for different recovery actions using a local ML model.
3. **Validates** the ML recommendation against strict deterministic business policies.
4. **Executes** the approved action safely (simulated).
5. **Evaluates** the real-world outcome, calibrates the model, and monitors for data drift.

## 3. Architecture & Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI, Python 3.11+ |
| **Database** | SQLite + SQLAlchemy ORM |
| **Machine Learning** | scikit-learn (Random Forest Classifier) |
| **Data Processing** | pandas, joblib |
| **Frontend** | Vanilla HTML/CSS/JS (real-time polling) |

### System Flow

```
Razorpay-style Webhooks
    → Event Ingestion & Normalization
    → Persistence (SQLite)
    → Detection Engine (Priority Scoring)
    → Recovery Candidate
    → Feature Extraction
    → ML Prediction (Local Random Forest)
    → Policy Engine (Deterministic Rules)
    → Recovery Orchestrator (State Machine)
    → Simulated Execution
    → Recovery Outcome
    → Feedback Ledger
    → Model Evaluation & Drift Monitoring
    → Model Governance (Manual Promotion)
```

For detailed breakdowns, see:
- [Architecture](docs/ARCHITECTURE.md) — Component descriptions and data flow diagram
- [Safety Guidelines](docs/SAFETY.md) — Retry limits, fraud blocks, idempotency rules
- [Data Lineage](docs/DATA_LINEAGE.md) — Feature vs. label separation, leakage protection

## 4. Custom ML Approach

The system uses a **local tabular ML model** (scikit-learn Random Forest Classifier) to predict:

```
P(success | candidate, RETRY)
P(success | candidate, PAYMENT_UPDATE)
P(success | candidate, ESCALATE)
```

The action with the highest **expected recovery value** (`P(success) × amount`) is recommended.

**Features used at inference time:**
- `customer_segment`, `payment_method`, `error_code`
- `amount_relative`, `retry_count`
- `hour`, `day_of_week`
- `hist_payment_count`, `hist_success_rate`

**NOT used at inference time (leakage-protected):**
- `actual_outcome`, `recovered_amount`, `failure_reason`

The model provides deterministic, explainable predictions with no external API dependency.

## 5. Safety Model

The system enforces strict safety boundaries:

- **Retry Limit:** Maximum 3 retries per payment. Further attempts are `BLOCKED`.
- **Fraud Block:** `suspected_fraud` error codes are hard-blocked from automated retries.
- **Dispute Block:** `customer_dispute` error codes are hard-blocked.
- **Account Closed Block:** `account_closed` error codes are hard-blocked.
- **Idempotency:** Actions are keyed by `candidate_id + action_type + attempt_number`. Duplicate requests return `409 Conflict`.
- **Simulator-Only:** `PAYMENT_EXECUTION_MODE: Literal["SIMULATED"]` — cannot be overridden.
- **No Automatic Retraining:** Drift is measured; retraining is recommended but never automatic.
- **No Automatic Promotion:** Models must be explicitly validated and promoted via CLI.

## 6. Recovery Orchestration

The orchestrator implements a deterministic state machine:

```
PENDING → VALIDATING → APPROVED → EXECUTING → SUCCEEDED / FAILED
                     → BLOCKED (policy violation)
```

Each transition is logged with structured JSON, and the state is persisted in SQLite with full idempotency guarantees.

## 7. Feedback Loop

After execution, outcomes are joined chronologically with predictions to produce:

- **Action Performance:** Success rate per action type
- **Revenue Metrics:** Total at risk, expected recovery, realized recovery
- **Calibration:** Predicted probability vs. actual recovery rate
- **Drift Monitoring:** Compares recent performance against historical baselines

If drift exceeds 15%, the system flags `RETRAIN_RECOMMENDED` but does **not** retrain automatically.

## 8. Model Governance

- Models start as `VALIDATED` in the registry.
- Promotion to `ACTIVE` requires explicit CLI invocation.
- Only one model can be `ACTIVE` at any time.
- Previous active models are automatically `RETIRED` upon promotion.

```powershell
python scripts/promote_model.py --version recovery-v2
```

---

## 9. Setup Instructions

**Prerequisites:**
- Python 3.11+
- Git

**Clone and install:**
```powershell
git clone https://github.com/rawcdr/AI-Revenue-Recovery.git
cd AI-Revenue-Recovery
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

**Initialize demo environment:**
```powershell
python scripts/setup_demo.py
```

**Run backend:**
```powershell
uvicorn backend.app.main:app --reload
```

**View dashboard:**
Open `frontend/index.html` in your browser.

**Reset environment:**
```powershell
python scripts/reset_demo.py
```

## 10. Demo Instructions

After running `setup_demo.py` and starting the backend:

**Scenario A — Network Error → RETRY → RECOVERED:**
```powershell
# The setup script creates a candidate with error_code=network_error
# Execute it via API:
curl -X POST http://127.0.0.1:8000/recovery/{SCENARIO_A_CANDIDATE_ID}/execute
# Expected: status=SUCCEEDED, result=SUCCESS
```

**Scenario B — Expired Card → PAYMENT_UPDATE → RECOVERED:**
```powershell
curl -X POST http://127.0.0.1:8000/recovery/{SCENARIO_B_CANDIDATE_ID}/execute
# Expected: status=SUCCEEDED, result=SUCCESS
```

**Scenario C — Suspected Fraud → POLICY BLOCK → ESCALATE:**
```powershell
curl -X POST http://127.0.0.1:8000/recovery/{SCENARIO_C_CANDIDATE_ID}/execute
# Expected: status=BLOCKED, reason contains "suspected_fraud"
```

The Candidate IDs are printed by `setup_demo.py` during initialization.

**Batch execution:**
```powershell
curl -X POST http://127.0.0.1:8000/recovery/execute
```

**View feedback and metrics:**
```
GET http://127.0.0.1:8000/metrics/feedback
GET http://127.0.0.1:8000/metrics/recent-activity
GET http://127.0.0.1:8000/intelligence/drift
GET http://127.0.0.1:8000/intelligence/models
```

## 11. API Information

Interactive Swagger documentation: `http://127.0.0.1:8000/docs`

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Basic health check |
| `/ready` | GET | Readiness check (DB + active model) |
| `/webhooks/razorpay` | POST | Ingest Razorpay-style webhook events |
| `/events` | GET | List normalized events |
| `/detection/run` | POST | Run candidate detection |
| `/detection/metrics` | GET | Detection statistics and revenue at risk |
| `/intelligence/{candidate_id}` | POST | Generate ML prediction for a candidate |
| `/intelligence/batch` | POST | Batch ML predictions |
| `/intelligence/models` | GET | List model registry |
| `/intelligence/drift` | GET | Drift and retraining status |
| `/recovery/queue` | GET | Active recovery queue |
| `/recovery/execute` | POST | Batch recovery execution |
| `/recovery/{id}/execute` | POST | Single candidate execution |
| `/recovery/{id}/actions` | GET | Action history for a candidate |
| `/metrics/feedback` | GET | Feedback, calibration, revenue metrics |
| `/metrics/recent-activity` | GET | Recent activity with ML explanations |

## 12. Limitations

- **Synthetic Data:** All data is generated by `Faker`. ML metrics reflect synthetic distributions, not production performance.
- **Simulated Execution:** No real payment processing occurs. The simulator uses deterministic logic based on error codes.
- **Single-Node:** SQLite is used for simplicity. A production system would require PostgreSQL or similar.
- **No Real-Time Webhooks:** Events are seeded via script, not received from a live Razorpay integration.
- **Feature Simplification:** Historical customer features are approximated. A production system would compute them from actual transaction history.
- **No Authentication:** The API is unauthenticated for demo purposes.
