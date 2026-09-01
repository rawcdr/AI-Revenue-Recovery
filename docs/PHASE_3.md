# Phase 3: Detection & Revenue-at-Risk Intelligence

This phase implements a deterministic detection engine capable of analyzing current entity states, creating deduplicated recovery candidates, and assigning explainable priority scores for future intervention.

## Database Additions
- **`RecoveryCandidate` model added:**
  - Standardizes the queue of entities requiring attention (payments and subscriptions).
  - Includes explicit tracking of `state` (FAILED, PENDING, HALTED), `severity`, and `priority_score`.
  - Supports `status` (ACTIVE, RESOLVED) for lifecycle management.
  - Deduped automatically per `entity_id`.

## Detection Rules
The system detects the following conditions:
1. **Payments**: `payment.status == failed` -> `PAYMENT_FAILURE`
2. **Subscriptions**: `subscription.status == pending` -> `SUBSCRIPTION_PENDING`
3. **Subscriptions**: `subscription.status == halted` -> `SUBSCRIPTION_HALTED`

*Successful or captured payments are deliberately ignored or transition active candidates to RESOLVED.*

## Idempotency and State Management
- If detection runs repeatedly, new candidates are NOT blindly created. Existing candidates are queried by `entity_id`.
- If an entity undergoes state transitions (e.g., a subscription moves from `pending` to `halted`), the existing candidate is gracefully updated and its priority score recalculated.

## Priority Formula
The system assigns a preliminary, explainable priority score:
`Priority Score = amount × customer_factor × state_factor × retry_factor`

- **Customer Factors**: `high_value` (1.5), `standard` (1.0), `new` (0.8)
- **State Factors**: `SUBSCRIPTION_HALTED` (1.5), `SUBSCRIPTION_PENDING` (1.2), `PAYMENT_FAILURE` (1.0)
- **Retry Factors**: `0` (1.0), `1` (1.1), `2` (1.2), `3+` (0.5) (Penalizing hopelessly failed items).

## Severity Classification
Failures are deterministically triaged:
- **Low**: `network_error`, `gateway_failure`, `bank_timeout`
- **Medium**: `insufficient_funds`, `card_declined`, `expired_card`, `invalid_payment_method`
- **High**: `customer_dispute`, `suspected_fraud`, `account_closed`

## Recovery Queue and Metrics Integration
- **`GET /recovery/queue`** now pulls directly from active `RecoveryCandidate` rows, properly ordered by `priority_score DESC`.
- **`GET /metrics/revenue-at-risk`** directly sums the `amount` of all active candidates ensuring perfectly synchronized reporting without double-counting historical events.

## Operation
Execute the detection logic passively without invoking webhooks via the script:
```bash
python scripts/run_detection.py
```
Or via the REST API:
```text
POST /detection/run
```

## Phase 4 Boundary Limitations
This phase introduces purely deterministic evaluation. There are NO Large Language Model integrations, AI-based generative reasoning layers, dynamic automated execution, or policy engines running yet. All detected reasonings are hard-coded templates matching the state triggers.
