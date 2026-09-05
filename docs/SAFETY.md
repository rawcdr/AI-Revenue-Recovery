# Safety Boundaries & Configurations

This project enforces strict safety boundaries to ensure deterministic behavior, avoid unintended execution of real payments, and prevent hallucinations.

## 1. Simulator-Only Execution

The system is hardcoded to operate in simulation mode.
- **Configuration:** `PAYMENT_EXECUTION_MODE: Literal["SIMULATED"] = "SIMULATED"` in `config.py`.
- **Type Enforcement:** The type annotation is `Literal["SIMULATED"]`, not `str`. Pydantic will reject any other value at application startup — even if set via environment variable or `.env` file.
- **Execution Path:** The orchestrator calls exclusively `simulate_execution()`. There is zero integration with live Razorpay APIs, no HTTP client to external payment gateways, and no payment SDK installed.

## 2. No External Foundation Models

- **Boundary:** There is no reliance on external LLMs (Claude, OpenAI, Gemini, Anthropic, Hugging Face Inference, etc.).
- **Enforcement:** The `validate_project.py` script actively scans the codebase and Python environment for banned AI SDKs (`openai`, `anthropic`, `google-generativeai`, `transformers`).
- **Reasoning:** Financial recovery decisions require 100% determinism, explainability, and latency guarantees that external generative models cannot provide. All intelligence is powered by a local `scikit-learn` Random Forest model.

## 3. Strict Policy Constraints

The Policy Engine (`policy.py`) evaluates all generated actions before execution.

| Rule | Enforcement |
|---|---|
| **Retry Limit** | Hard cap at 3 retry attempts (`MAX_RETRY_ATTEMPTS = 3`). Further attempts → `BLOCKED`. |
| **Fraud Block** | `suspected_fraud` error code → automated retries `BLOCKED`. |
| **Dispute Block** | `customer_dispute` error code → automated retries `BLOCKED`. |
| **Account Closed Block** | `account_closed` error code → automated retries `BLOCKED`. |
| **Action Whitelist** | Only `RETRY`, `PAYMENT_UPDATE`, and `ESCALATE` are supported. |
| **Escalation** | `ESCALATE` is always approved (it is a workflow transition, not a payment action). |

## 4. Idempotency

- **Action Key:** Each action is uniquely identified by `candidate_id + action_type + attempt_number`.
- **Duplicate Detection:** If a request arrives with an idempotency key that already exists in the database, the system returns `HTTP 409 Conflict` instead of creating a duplicate.
- **State Conflict:** If a candidate is no longer `ACTIVE` (e.g., already `RESOLVED`), the system returns `HTTP 409 Conflict`.

## 5. Model Governance

- **No Autonomous Retraining:** The system measures drift via `drift.py` and will recommend retraining (`RETRAIN_RECOMMENDED`) if performance drops >15%, but it will **never** automatically launch a training job.
- **No Autonomous Promotion:** A newly trained model must be explicitly marked as `VALIDATED` and manually promoted via the `scripts/promote_model.py` CLI tool. Only one model can be `ACTIVE` at a time; the previous active model is automatically `RETIRED`.
