# Phase 2: Event Ingestion + Normalization + Persistence

This phase transitions the synthetic dataset into a live, event-driven backend system powered by FastAPI and SQLite, ready to accept webhooks and track revenue at risk.

## Database Architecture
- **Engine**: SQLite (`recovery.db`)
- **ORM**: SQLAlchemy
- **Tables**:
  - `customers`: Customer profiles and segmentation data.
  - `payments`: Tracks lifecycle of one-time transactions.
  - `subscriptions`: Manages recurring plan states (active, pending, halted).
  - `events`: Immutable log of normalized webhook events.

## Webhook Processing Flow
The `POST /webhooks/razorpay` endpoint serves as the system's ingestion gateway.

1. **Receive & Validate**: Accepts an arbitrary `WebhookPayload` matching a supported Razorpay-style event. 
2. **Normalize**: The `event_normalization.py` service extracts the nested JSON entity and flattens it into a standardized `NormalizedEvent` model.
3. **Idempotency Check**: The `event_ingestion.py` service queries the `events` table by `event_id`. Duplicates are silently dropped and return `{"status": "duplicate"}`.
4. **Persist Event**: The event is appended to the immutable `events` log.
5. **State Transition**: The ingestion service predictably updates the core entity's state (e.g., transitioning a payment's status to `failed` and logging the timestamp).

## Supported Events
Only events relevant to the current recovery scope are accepted:
- `payment.created`, `payment.failed`, `payment.authorized`, `payment.captured`
- `subscription.created`, `subscription.pending`, `subscription.halted`
- `checkout.created`, `checkout.abandoned`, `checkout.completed`

## API Endpoints
- `GET /health`: Core system check.
- `POST /webhooks/razorpay`: Ingests and routes webhooks.
- `GET /events`: Retrieves the recent normalized event log.
- `GET /recovery/queue`: Exposes failed payments and pending/halted subscriptions, prioritized deterministically via `amount * customer_value_factor`.
- `GET /metrics/revenue-at-risk`: Dynamically computes total revenue blocked in `failed` payments and `pending`/`halted` subscriptions via direct SQL aggregations.

## Database Seeding
The Phase 1 synthetic dataset can be injected directly into SQLite using:
```bash
python scripts/seed_database.py --reset
```
This is fully idempotent (per primary keys) and supports resetting the DB to a clean state.

## Known Limitations & Future Hardening
- **Security**: Webhook signature verification (e.g. `X-Razorpay-Signature`) is bypassed for this phase but must be implemented for production security.
- **MRR vs Invoices**: Subscriptions expose `mrr_value` which is used for risk calculation. In a production environment with Razorpay, a halted subscription would ideally tie directly to unpaid distinct `invoice` entities.
- **Queueing Engine**: The recovery queue is a simple GET endpoint wrapping a synchronous database query. Future implementations should adopt an asynchronous task queue (e.g. Celery).
