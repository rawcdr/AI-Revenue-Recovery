# Phase 0: Project Foundation & Scope Lock

### Product

**Revenue Recovery Agent**

### One-line description

An AI-assisted payment recovery system that detects failed payments, diagnoses likely root causes, recommends bounded recovery actions, enforces deterministic safety rules, and measures successfully recovered revenue.

### Primary scenarios

1. Failed one-time payments
2. Failed subscription payments / halted subscriptions

### Optional later scenario

3. Checkout abandonment

### Initial recovery actions

Only:

* `RETRY`
* `PAYMENT_UPDATE`
* `ESCALATE`

### Safety principles

1. Maximum 3 automated retries for an individual payment/recovery flow.
2. Do not retry known unrecoverable cases.
3. Do not automatically retry customer-disputed transactions.
4. Escalate low-confidence or policy-sensitive cases.
5. Never modify the amount being recovered.
6. LLM output is only a recommendation.
7. Deterministic policy logic decides whether an action is allowed.
8. Every eventual action must be auditable.
9. Automation must have explicit stopping rules.

### Out of scope for the initial implementation

* Hinglish voice agent
* B2B receivables
* Real SMS infrastructure
* Real customer communication infrastructure
* Production payment processing
* Autonomous arbitrary money movement
* Complex ML model training
* Large distributed infrastructure
* Large numbers of recovery strategies

These may be considered only after the core recovery flow works.

### Phase Boundaries

Phase 0 does NOT implement:

* Synthetic dataset generation
* Payment/subscription schemas
* Razorpay webhook processing
* LLM diagnosis
* Recovery execution
* Policy engine
* Dashboard
* Evaluation metrics

Those belong to later phases.

The next phase will focus on:

**Phase 1 — Data model + synthetic Razorpay-style dataset**
