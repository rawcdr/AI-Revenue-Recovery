# Phase 1: Data Model + Synthetic Dataset

This phase establishes the foundational data layer for the Revenue Recovery Agent, providing a reproducible, synthetic workload simulating Razorpay-style payment failures, subscriptions, and checkout events.

## Dataset Architecture

The dataset is relational, generated deterministically from seed `42`, and located in `data/generated/`.

* `customers.csv`: Synthetic customer profiles with segmentation and risk tiers.
* `payments.csv`: One-time payment records, capturing success and failure statuses.
* `subscriptions.csv`: Recurring subscription plans (`plan_basic`, `plan_pro`, `plan_business`) with active, pending, and halted states.
* `checkout_sessions.csv`: Checkout lifecycle records (completed or abandoned).
* `payment_events.csv`: A chronologically ordered event stream correlating all entity state transitions.

## Failure Taxonomy & Ground Truth Strategy

The dataset uses a weighted taxonomy of synthetic failures:
* `insufficient_funds` (25%)
* `card_declined` (20%)
* `gateway_failure` (15%)
* `network_error` (10%)
* `expired_card` (10%)
* `invalid_payment_method` (7%)
* `bank_timeout` (5%)
* `customer_dispute` (3%)
* `suspected_fraud` (3%)
* `account_closed` (2%)

### Ground-Truth Labels
Each relevant failure includes explicitly calculated ground truth:
* `recoverable`: Boolean logic (with slight randomization for realism). E.g. `insufficient_funds` is True, `suspected_fraud` is False.
* `ground_truth_root_cause`: The actual taxonomy category generating the failure.
* `ground_truth_action`: Deterministic allowed actions: `RETRY`, `PAYMENT_UPDATE`, or `ESCALATE`.

## Dataset Generation and Validation

### Generation Command
```bash
python scripts/generate_dataset.py
```
This script leverages `Faker` (seeded) to predictably generate hundreds of records spanning ~60 days of synthetic time history.

### Validation Command
```bash
python scripts/validate_dataset.py
```
This script enforces rigorous checks:
- Verifies referential integrity between events, entities, and the customer table.
- Validates temporal ordering (e.g. `failed_at` must occur after `created_at`).
- Ensures valid INR amounts > 0.
- Checks enum values and bounds logic.

## Dataset Statistics (Example Run)

* Customers: 200
* Payments: 300 (90 Failed -> 80 Recoverable, 10 Unrecoverable)
* Subscriptions: 100 (15 Pending, 12 Halted)
* Checkout Sessions: 150 (61 Abandoned)
* Events: >1200 records

## Design Assumptions & Known Limitations
- The random distributions (e.g., failure percentages) are meant for robust synthetic testing, not as an exact replica of live production statistics.
- Financial figures are whole integers or standard pricing (e.g., 499, 1499) for simplicity.
- The dataset assumes a single currency (`INR`).
