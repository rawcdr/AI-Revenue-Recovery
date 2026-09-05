# Revenue Recovery Agent

An AI-assisted payment recovery system for failed Razorpay-style payments.

**Current Phase:** Phase 0 (Project Foundation & Scope Lock)

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

2. Activate the virtual environment (Windows):
   ```bash
   .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

Start the FastAPI backend server:
```bash
python run.py
```

The health endpoint will be available at: http://127.0.0.1:8000/health

## Running Tests

Run the basic health check tests:
```bash
pytest
```

## Documentation

* [Phase 0 Scope Document](docs/PHASE_0.md)
* [Phase 1 Dataset Document](docs/PHASE_1.md)

## Phase Data

- [x] Phase 4: Custom Recovery Intelligence Engine (Scikit-Learn, Random Forest/Logistic Regression, Feature Engineering)
- [x] Phase 5: Bounded Recovery Action Orchestrator (Deterministic State Machine, Safety Guardrails)
- [x] Phase 6: Recovery Feedback, Model Evaluation, Drift Monitoring, and Explicit Promotions

To generate the synthetic dataset and seed the SQLite database:
```bash
python scripts/seed_database.py --reset
```

To run dataset assertions:
```bash
python scripts/validate_dataset.py
```

## Run Detection Engine (Phase 3)

The deterministic detection engine builds the queue and calculates revenue at risk:
```bash
python scripts/run_detection.py
```
