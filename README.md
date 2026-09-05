# AI Revenue Recovery Agent

A fully bounded, deterministic, tabular-ML-driven orchestrator designed to intelligently recover failed payments and halted subscriptions for the Razorpay Buildathon.

**IMPORTANT DISCLAIMERS:**
- **Synthetic Data:** The dataset is entirely synthetic. No real PII or payment data is used.
- **Simulator-Only:** Payment execution is **simulated**. The system does not possess real payment credentials and cannot capture actual funds.
- **No External LLMs:** This system does **not** use Claude, OpenAI, Gemini, or any external foundation models. All predictions are generated locally using scikit-learn.
- **Strict Guardrails:** The system operates under strict deterministic policies (e.g., hard block on suspected fraud, max 3 retries).

---

## 1. Problem
Failed payments and halted subscriptions lead to massive involuntary churn for merchants. Recovering these payments blindly via brute-force retries incurs high network costs, triggers fraud flags, and alienates customers. 

## 2. Solution
An intelligent, closed-loop orchestrator that:
1. Ingests webhook events to detect halted payments.
2. Uses a local ML model (Random Forest) to predict the probability of success for different recovery actions (`RETRY`, `PAYMENT_UPDATE`, `ESCALATE`).
3. Validates the ML recommendation against strict deterministic business policies.
4. Executes the approved action safely (simulated).
5. Closes the loop by evaluating the real-world outcome, calibrating the model, and monitoring for data drift.

## 3. Architecture & Tech Stack
- **Backend:** FastAPI, Python 3.11+
- **Database:** SQLite + SQLAlchemy ORM
- **Machine Learning:** `scikit-learn`, `pandas` (Random Forest Classifier)
- **Frontend:** Vanilla HTML/CSS/JS (Lightweight, real-time polling)

For a detailed breakdown, see [Architecture](docs/ARCHITECTURE.md), [Safety Guidelines](docs/SAFETY.md), and [Data Lineage](docs/DATA_LINEAGE.md).

---

## 4. Quick Setup & Demo

**Prerequisites:**
- Python 3.11+
- Virtual environment active

**Install dependencies:**
```powershell
pip install -r requirements.txt
```

**Initialize Demo Environment:**
This command validates the synthetic dataset, resets the SQLite database, seeds it, registers the ML model, and generates deterministic scenarios.
```powershell
python scripts/setup_demo.py
```

**Run the Backend:**
```powershell
uvicorn backend.app.main:app --reload
```
The health endpoint is available at `http://127.0.0.1:8000/health`. Swagger documentation is at `http://127.0.0.1:8000/docs`.

**View the Dashboard:**
Open `frontend/index.html` in your browser.

**Reset Environment:**
To clear all data and start fresh:
```powershell
python scripts/reset_demo.py
```

---

## 5. Example Recovery Workflow

1. **Detection:** A `payment.failed` webhook is ingested. The Detection engine identifies it, scores its priority, and marks it as an `ACTIVE` `RecoveryCandidate`.
2. **Intelligence:** The `score_candidate` function extracts candidate features (amount, retry count, customer segment) and queries the active ML model, which predicts a 82% success rate for `RETRY`.
3. **Policy Engine:** The Orchestrator intercepts the `RETRY` command. The Policy Engine verifies the payment error is *not* fraud, and the retry count is under 3. It approves the action.
4. **Execution:** The Simulator deterministically processes the retry. If the simulated network request succeeds, the outcome is logged as `RECOVERED`.
5. **Feedback Loop:** The `/metrics/feedback` endpoint chronologically joins the prediction and the outcome, updating the model's calibration buckets and overall recovery rate in the dashboard.

---

## 6. Model Governance & Safety

**Manual Model Promotion:** 
Models are never promoted autonomously. To promote a model, it must be explicitly validated by an engineer:
```powershell
python scripts/promote_model.py --version recovery-v2
```

**Drift Detection:** 
The system actively compares recent recovery feedback against historical baselines. If absolute performance drops by >15%, the system raises a `RETRAIN_RECOMMENDED` flag. It will *not* retrain automatically.
