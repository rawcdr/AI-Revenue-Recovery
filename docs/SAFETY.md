# Safety Boundaries & Configurations

This project enforces strict safety boundaries to ensure deterministic behavior, avoid unintended execution of real payments, and prevent hallucinations.

## 1. Simulator-Only Execution
The system is hardcoded to operate in simulation mode. 
- **Configuration:** `PAYMENT_EXECUTION_MODE = "SIMULATED"` is strictly enforced in `config.py`.
- **Enforcement:** The `execute_action()` method in the orchestrator routes exclusively to `simulate_execution()`. There is zero integration with live Razorpay APIs for actual payment capture.

## 2. No External Foundation Models
- **Boundary:** There is no reliance on external LLMs (Claude, OpenAI, Gemini, etc.).
- **Enforcement:** The `validate_project.py` script actively scans the codebase and python environment to ensure banned AI SDKs and API calls are not present.
- **Reasoning:** Financial recovery decisions require 100% determinism, explainability, and latency guarantees that external generative models cannot provide. All intelligence is powered by local `scikit-learn` models.

## 3. Strict Policy Constraints
The Policy Engine evaluates all generated actions before execution.
- **Retry Limits:** Candidates are hard-capped at 3 retry attempts. Any further attempts are `BLOCKED`.
- **Fraud/Dispute Blocks:** Any entity with an error code of `suspected_fraud`, `customer_dispute`, or `account_closed` is strictly prohibited from automated retries and is instantly escalated.
- **Action Whitelist:** The system only supports `RETRY`, `PAYMENT_UPDATE`, and `ESCALATE`.

## 4. Model Governance
- **No Autonomous Retraining:** The system measures drift and will recommend retraining (`RETRAIN_RECOMMENDED`), but it will never automatically launch a training job.
- **No Autonomous Promotion:** A newly trained model must be explicitly marked as `VALIDATED` and manually promoted via the `scripts/promote_model.py` CLI tool.
- **Idempotency:** Action generation uses deterministic hashes (`candidate_id + action_type + attempt_number`) to guarantee duplicate execution requests are ignored.
