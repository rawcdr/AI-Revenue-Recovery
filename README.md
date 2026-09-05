# AI Revenue Recovery Engine

An intelligent, closed-loop payment recovery system that identifies revenue at risk, predicts the optimal recovery action via local ML, enforces deterministic safety policies, and orchestrates bounded simulated execution.

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4.1.svg)
![SQLite](https://img.shields.io/badge/SQLite-Database-blue.svg)
![Tests](https://img.shields.io/badge/Tests-37%20Passed-brightgreen.svg)

> **Synthetic Data Disclaimer:** The dataset is entirely synthetic. No real PII or payment data is used. The ML metrics are based on synthetic data and should not be interpreted as production performance.
> 
> **Simulated Payment Disclaimer:** Payment execution is **simulated**. The system does not possess real payment credentials and cannot capture actual funds.
> 
> **No External AI Disclaimer:** No external LLM or foundation model is used. This system does **not** use Claude, OpenAI, Gemini, Anthropic, Hugging Face Inference, or any hosted AI service. All predictions are generated locally using scikit-learn.

---

## 1. The Problem

Failed payments and halted subscriptions lead to massive involuntary churn. However, payment failures are not all the same. Consider the following scenarios:
- Insufficient funds
- Network failures
- Expired cards
- Gateway timeouts
- Suspected fraud
- Customer disputes

A naive recovery system might brute-force retry every failure. This is expensive, alienates customers, and triggers fraud flags at the issuing bank. An intelligent system must answer: *"Given this specific failed payment context, what should we do next?"*

Possible actions:
- **RETRY** (e.g., for a network failure or temporary funds issue)
- **PAYMENT_UPDATE** (e.g., prompting the user for a new card if expired)
- **ESCALATE** (e.g., suspending the service and alerting a human for fraud)

The objective is to **maximize expected recoverable revenue while strictly respecting business safety constraints**.

## 2. What I Built

This project is a complete, end-to-end recovery lifecycle system. It moves beyond a standalone ML model to orchestrate the entire decision flow.

The system includes:
- **Event Ingestion & Normalization:** Capturing synthetic webhook events.
- **Candidate Detection:** Identifying active failures and calculating revenue at risk.
- **Feature Engineering:** Extracting inference-time context (without outcome leakage).
- **Custom ML Recovery Intelligence:** Predicting success probabilities for various actions.
- **Deterministic Policy Engine:** Overriding or approving ML recommendations based on hard business rules (e.g., never retry fraud).
- **Bounded Orchestration:** Safely managing the state machine transitions (PENDING → EXECUTING).
- **Simulated Execution:** Deterministically returning a success or failure outcome.
- **Outcome Recording & Feedback:** Closing the loop to build historical ledgers.
- **Evaluation & Model Registry:** Monitoring for drift and managing manual model promotion.
- **Dashboard:** A visual overview of active candidates and recovery metrics.

## 3. Target

The core intelligence target is predicting:

`P(success | candidate context, action)`

for:
- `RETRY`
- `PAYMENT_UPDATE`
- `ESCALATE`

The system then selects the action that maximizes **Expected Recovery Value**:
`Expected Recovery Value = payment_amount × probability of successful recovery`

*Crucially, the ML model only recommends. A deterministic safety policy can override the ML recommendation to block unsafe actions.*

## 4. System Flow

```text
Razorpay-like Events
        ↓
Event Normalization
        ↓
Recovery Candidate Detection
        ↓
Feature Engineering
        ↓
Custom Recovery Intelligence
        ↓
Action Probabilities
        ↓
Expected Recovery Value
        ↓
Safety & Recovery Policy
        ↓
Bounded Recovery Orchestrator
        ↓
Simulated Payment Execution
        ↓
Recovery Outcome
        ↓
Feedback Dataset
        ↓
Model Evaluation
        ↓
Model Registry / Drift Monitoring
```

- **Events to Detection:** Webhooks arrive and are persisted. The system scans for unresolved failures.
- **Intelligence to Policy:** Features are fed to the local ML model. It outputs probabilities. The highest expected value action is proposed. The Policy Engine reviews it.
- **Policy to Execution:** If approved, the orchestrator triggers the Simulator. The simulator returns a deterministic outcome.
- **Outcome to Feedback:** The attempt is logged chronologically to evaluate drift and train future models.

## 5. Architecture

| Component | Responsibility |
|-----------|----------------|
| **Backend / FastAPI** | Core API serving the webhooks, orchestrator, and metrics. |
| **Database / SQLite** | Local relational persistence for all entities and candidates. |
| **Detection** | Polls events to identify and prioritize active recovery candidates. |
| **Intelligence** | Computes expected values using local `scikit-learn` models. |
| **Policy** | Hardcoded deterministic constraints (e.g., max 3 retries, fraud blocking). |
| **Orchestrator** | Idempotent state machine that executes the recovery attempt securely. |
| **Simulator** | Safely mocks Razorpay execution outcomes based on context. |
| **Feedback** | Generates a training-ready ledger joining candidates, predictions, and outcomes. |
| **Evaluation** | Assesses historical performance and drift. |
| **Model Registry** | Governs which model is ACTIVE vs VALIDATED. |
| **Frontend** | Vanilla HTML/JS dashboard visualizing revenue at risk and model explanations. |
| **Scripts** | Utilities for demo setup, dataset generation, training, and validation. |
| **Tests** | Comprehensive `pytest` suite ensuring idempotency and policy enforcement. |

## 6. Custom ML Intelligence

This system deliberately **does not** rely on external LLMs or APIs for its recovery intelligence. 

Instead, it uses a custom local tabular ML engine trained on 20,000 synthetic scenarios. 

- **Data Separation:** Implements strict customer-level train/validation/test separation (`GroupShuffleSplit`) to prevent behavioral leakage.
- **Algorithms:** Compares a `LogisticRegression` baseline against a `RandomForestClassifier`.
- **Calibration:** Uses `CalibratedClassifierCV` (Isotonic/Sigmoid) to ensure predictions are true probabilities.
- **Evaluation Metrics:** Evaluated on ROC-AUC and Brier Score (measured purely on synthetic data).
- **Persistence:** Models are serialized using `joblib` (`models/recovery_intelligence.joblib`) for sub-millisecond local inference.

## 7. Features Used

The ML model predicts based on inference-time features explicitly designed to prevent target leakage.

**Payment Context:**
- `amount` (standardized)
- `payment_method` (e.g., card, UPI)
- `error_code` (e.g., network_error, expired_card)
- `retry_count`

**Customer History:**
- `customer_segment`
- `hist_payment_count`
- `hist_success_rate`

**Temporal/Contextual Features:**
- `hour`
- `day_of_week`

## 8. Recovery Policy & Safety

The policy engine is the final authority. It is designed around the principle: **The model recommends; the policy decides.**

Key constraints:
- **Maximum Retries:** Capped at 3 attempts per payment.
- **Idempotency:** HTTP 409 enforcement prevents accidental duplicate executions of the same attempt.
- **Simulated-Only Execution:** `PAYMENT_EXECUTION_MODE` is strictly locked to `Literal["SIMULATED"]`.
- **Manual Promotion:** Models can only be promoted from `VALIDATED` to `ACTIVE` by explicit manual script. No autonomous rollouts.

**Hard Blocks:**
The policy engine intercepts and permanently blocks autonomous retries for:
- `suspected_fraud`
- `customer_dispute`
- `account_closed`

This ensures that even if a model misbehaves or evaluates a high expected value on a large transaction, policy safety prevents execution.

## 9. Demo Scenarios

The demo provides reproducible, deterministic simulations of the recovery flow:

| Scenario | Trigger | Expected Flow |
|----------|---------|---------------|
| **Scenario A** | `network_error` | ML recommends **RETRY** → Policy Approves → Simulator SUCCEEDS → `RECOVERED` |
| **Scenario B** | `expired_card` | ML recommends **PAYMENT_UPDATE** → Policy Approves → Simulator SUCCEEDS → `RECOVERED` |
| **Scenario C** | `suspected_fraud` | ML recommends RETRY (due to high amount expected value) → **Policy BLOCKS** → Engine routes to `ESCALATE` |

## 10. Dashboard

The frontend (`frontend/index.html`) is a lightweight browser dashboard that displays:
- Total Revenue at Risk (Synthetic INR)
- Active Candidate details
- Real-time action distributions
- ML confidence/probability explanations
- Recent activity ledgers

## 11. Data

The dataset consists of generated synthetic Razorpay-like events. It contains tables for Customers, Payments, Subscriptions, and Payment Events. 

The initial demo seed is generated deterministically to ensure a reproducible evaluation environment. **No real customer or payment data is included in this repository.**

## 12. Tech Stack

| Technology | Purpose |
|------------|---------|
| Python | Primary backend language. |
| FastAPI | High-performance API framework. |
| SQLAlchemy | Relational ORM mapping. |
| SQLite | Local zero-config persistence. |
| Pydantic | Schema validation and serialization. |
| scikit-learn | Local tabular machine learning modeling. |
| pandas | Data manipulation and feature extraction. |
| joblib | Model serialization. |
| pytest | Comprehensive test runner. |
| Faker | Synthetic data generation. |
| HTML/CSS/JS | Dashboard frontend. |

## 13. Project Structure

```text
razorpay/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── core/         # Config and Logging
│   │   ├── db/           # SQLite Session config
│   │   ├── intelligence/ # Feature extraction and scoring
│   │   ├── models/       # SQLAlchemy domain models
│   │   ├── schemas/      # Pydantic validation schemas
│   │   └── services/     # Orchestrator, Policy, Simulator
│   ├── main.py
│   └── tests/            # 37 passing pytest tests
├── data/                 # Seeded synthetic datasets
├── docs/                 # Architectural documentation
├── frontend/             # HTML Dashboard
├── models/               # Serialized .joblib artifacts
├── scripts/              # Setup, validation, training CLI tools
├── requirements.txt
├── pytest.ini
└── README.md
```

## 14. How to Run

*Development targets Windows primarily, though macOS/Linux are supported.*

```bash
# 1. Clone the repository
git clone https://github.com/rawcdr/AI-Revenue-Recovery.git
cd AI-Revenue-Recovery

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize the deterministic demo state
python scripts/setup_demo.py

# 5. Start the backend server
uvicorn backend.app.main:app --reload
```

**Access Points:**
- Dashboard: Open `frontend/index.html` in your browser.
- Swagger API Docs: http://127.0.0.1:8000/docs
- Health Check: `GET http://127.0.0.1:8000/health`
- Readiness: `GET http://127.0.0.1:8000/ready`

## 15. Demo Walkthrough

To easily demonstrate the system's capabilities:

1. Run `python scripts/setup_demo.py` to seed the database and register the active model. Note the **Candidate IDs** printed in the terminal for Scenarios A, B, and C.
2. Open `frontend/index.html` to review the current active Revenue at Risk.
3. Open the Swagger UI at http://127.0.0.1:8000/docs.
4. Execute **Scenario A**: Use `POST /recovery/{candidate_id}/execute` with the Scenario A ID. The system will retry the network error successfully.
5. Execute **Scenario C**: Use the Scenario C ID. Watch the policy engine explicitly block the ML recommendation due to suspected fraud.
6. Refresh the dashboard to observe the recovered revenue and updated metrics.

## 16. API Overview

The FastAPI backend exposes the following primary router groups:

- **Health & Readiness:** Standard probes for deployment checks.
- **Webhooks:** Ingestion endpoints for raw event payloads.
- **Candidate Detection:** Triggers for priority scoring and scanning.
- **ML Intelligence:** Direct batch and granular candidate scoring.
- **Recovery Execution:** Core orchestrator invocation endpoints.
- **Metrics & Feedback:** Aggregations for the dashboard UI.
- **Events:** Normalized event queries.

*For full schemas and interactive testing, visit the Swagger UI (`/docs`).*

## 17. Testing

The repository contains a robust suite of integration and unit tests covering every layer of the architecture.

Currently, **37 tests are passing**. Coverage ensures:
- Webhook normalization and idempotency.
- Feature extraction and leakage prevention.
- Policy engine constraints (e.g., maximum retries).
- The state transitions inside the bounded orchestrator.
- Model registry promotion validations.

To run tests:
```bash
pytest backend/tests -v
```

## 18. Model Governance

Model deployment is strictly controlled.
- A newly trained model is placed in a **VALIDATED** state.
- It cannot make API predictions until explicitly promoted to **ACTIVE** via `scripts/promote_model.py`.
- There is **no automatic production promotion**, and the system monitors dataset drift to generate manual retraining recommendations instead of autonomous retraining loops.

## 19. Limitations

- **Synthetic Context:** The database uses synthetic data and simulated execution. Real Razorpay gateway API calls are intentionally omitted.
- **Persistence:** Relies on local SQLite for ease of demonstration, rather than a production-grade PostgreSQL cluster.
- **Performance Translation:** The recovery probabilities and evaluation metrics reflect synthetic scenarios. They should not be interpreted as guaranteed business metrics in a live production environment.

## 20. Future Improvements

- Implementing production PostgreSQL persistence.
- Integrating real Razorpay payment execution behind strict API key controls.
- Enabling an asynchronous distributed task queue (e.g., Celery/Redis) for batch execution.
- Advanced causal modeling (A/B testing) to determine uplift precisely.

## 21. Why This Project?

The most critical aspect of this repository is not simply the ML model. It is the integration of prediction into a governed, end-to-end decision system:

`Prediction → Decision → Safety Policy → Execution → Outcome → Feedback → Evaluation`

By bounding the ML intelligence with deterministic business constraints, this project demonstrates how AI can be safely deployed into high-risk, financially sensitive domains.

## 22. Buildathon Note

This project is a research-style demonstration created for the Razorpay Buildathon. It uses synthetic data and simulated payment execution. No real payments are processed, no real customer data is included, and no external LLM dependencies are required.
