# Phase 5: Recovery Action Orchestrator

This phase introduces a bounded action orchestrator that bridges the Phase 4 ML Recommendation engine to a simulated execution environment, strictly governed by a deterministic Policy Layer.

## Architecture

The orchestration lifecycle operates as an explicit state machine for each `RecoveryAction`:

`PENDING` → `VALIDATING` → `APPROVED` → `EXECUTING` → `SUCCEEDED` / `FAILED`

Or if rejected by policy:

`PENDING` → `VALIDATING` → `BLOCKED`

### 1. Deterministic Policy Guardrails
The system guarantees that ML models **cannot** override safety rules. The `policy.py` module evaluates candidate actions entirely independently of the ML framework:
- **Maximum Retries Enforced**: A maximum of 3 automated retries is permitted per candidate.
- **Sensitive Failure Blocks**: Hardcoded blocks prevent any automated recovery on payments failing due to `suspected_fraud`, `customer_dispute`, or `account_closed`.
- **State Enforcement**: Only `ACTIVE` candidates can be processed.

### 2. Execution Simulator
`simulator.py` safely simulates execution logic without real money movement or customer interaction. 
- It uses deterministic boundary logic combined with pseudo-random distributions seeded deterministically by `candidate_id` hashes to yield predictable, yet probabilistically accurate, test results.
- Example: An `expired_card` will reliably fail a `RETRY` action but succeed on a `PAYMENT_UPDATE`.

### 3. Idempotency & Audit Trail
- **Idempotency**: Execution requests are uniquely identified using a deterministic idempotency key (`{candidate_id}_{action_type}_{attempt_number}`). If a duplicate request is submitted (e.g., via network retry), the orchestrator returns the existing action state rather than duplicating execution.
- **Audit Logging**: Every action, policy decision, and resulting recovery outcome is persistently written to the SQLite database (`recovery_actions`, `recovery_outcomes`).

### 4. Revenue Metrics
The API exposes `GET /metrics/recovery` which computes true revenue recovered. Double-counting is explicitly prevented by joining unique recovery outcomes against their successful origin action.

## Safety Boundaries Maintained
- **NO Real Execution**: No production Stripe/Razorpay endpoints are hit.
- **NO Customer Messaging**: No emails, SMS, or WhatsApp payloads are dispatched.
- **NO New External AI**: The system relies on the local Phase 4 ML models and deterministic policies. No LLMs were introduced.
