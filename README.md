# SettleTrace
Settlement Q&A Agent for Fintech Support.
## Problem
Support teams may need to manually investigate why a payment settlement was not processed. Evidence can be spread across a payment gateway, bank records and an internal ledger.
SettleTrace accepts a transaction ID, traces the records, reconciles them, identifies discrepancies, determines the settlement state and provides a support-friendly explanation. Missing or conflicting evidence is reported instead of guessed.
## Solution
```text
        Transaction ID
              |
              v
        FastAPI -> PostgreSQL
             / | \
        Gateway Bank Ledger
             \ | /
               v
   Deterministic Investigation
               |
               v
       Optional AI Explanation
```
The investigation engine determines what the data shows. The AI only explains the verified result.
## Workflow
```text
1. Enter transaction ID
2. Retrieve Gateway, Bank and Ledger records
3. Compare statuses, amounts, IDs and timestamps
4. Detect missing, duplicate, mismatched or conflicting records
5. Determine status, root cause, confidence and action
6. Generate an optional natural-language explanation
```
## Investigation Engine
Core logic: `app/services/investigation.py`
Supported scenarios:
- Normal settlement
- Bank delay
- Missing bank record
- Amount mismatch
- Missing ledger record
- Settlement not initiated
- Duplicate settlement
- Insufficient/conflicting evidence
The AI cannot change the deterministic result or invent evidence.
## CSV Data
`generate_data.py` creates 1,000 mock transactions:
```text
data/
├── gateway.csv
├── bank.csv
└── ledger.csv
```
The datasets share fields such as `transaction_id`, `payment_id`, `settlement_id`, `amount`, `timestamp` and `status`. The generator intentionally creates different settlement conditions.
| ID | Scenario |
|---|---|
| TXN-DEMO-001 | Normal settlement |
| TXN-DEMO-002 | Bank delay |
| TXN-DEMO-003 | Missing bank record |
| TXN-DEMO-004 | Amount mismatch |
| TXN-DEMO-005 | Missing ledger record |
| TXN-DEMO-006 | Settlement not initiated |
| TXN-DEMO-007 | Duplicate settlement |
The CSVs are imported into PostgreSQL as mock/test data.
## PostgreSQL
PostgreSQL stores:
```text
gateway_records
bank_records
ledger_records
```
The backend uses PostgreSQL, SQLAlchemy and psycopg.
Setup/import:
```text
scripts/init_db.py
scripts/import_csv.py
```
The database connection is configured through `DATABASE_URL`. Local development uses the `payment_settlement` database; deployment uses an accessible hosted PostgreSQL database.
## AI
AI code: `app/services/ai_explanation.py`
The model receives the structured investigation result, not unrestricted database access.
It explains:
```text
what happened
why
evidence
recommended action
uncertainty
```
It must not change the result or invent records, values or reasons.
Configuration:
```text
LLM_API_KEY
LLM_MODEL
LLM_BASE_URL
```
API keys are stored as environment variables and are not committed.
If the AI provider is unavailable, the deterministic investigation still works.
## Backend
```text
Python + FastAPI
SQLAlchemy + PostgreSQL + psycopg
Pydantic + Uvicorn
pytest
```
Endpoints:
```text
GET  /health
GET  /transactions/{transaction_id}
GET  /investigations/{transaction_id}
POST /investigations/{transaction_id}/explanation
```
## Frontend
The frontend uses React, Vite, JavaScript and CSS.
It provides transaction lookup, Gateway/Bank/Ledger status, investigation results, evidence, discrepancies, timeline, recommended action, demo cases and optional AI explanation.
The backend URL is configured with:
```text
VITE_API_BASE_URL
```
## Deployment
```text
Frontend: Vercel
Backend:  Render
Database: PostgreSQL
```
The Vercel frontend uses `VITE_API_BASE_URL` to call the Render backend.
Render runs FastAPI with:
```text
uvicorn app.api:app --host 0.0.0.0 --port $PORT
```
### Deployment Issue
The application worked locally but initially failed to communicate correctly after deployment. The Vercel frontend and Render backend run on different origins, and CORS initially blocked the production frontend.
The backend CORS configuration was updated to allow the production frontend URL. The production database and required environment variables were also configured. The deployed frontend and backend then communicated successfully.
## Testing
```powershell
python -m pytest -q
```
Frontend:
```powershell
cd frontend
npm run build
```
## Local Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```
Create PostgreSQL database:
```text
payment_settlement
```
Generate and import data:
```powershell
python generate_data.py
python scripts/init_db.py
python scripts/import_csv.py
```
Start backend:
```powershell
uvicorn app.api:app --reload --port 8000
```
Start frontend in another terminal:
```powershell
cd frontend
npm install
npm run dev
```
## Project Structure
```text
Settlement-Q-A-Agent-for-Fintech-Support-main/
├── app/
│   ├── api.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── repository.py
│   ├── schemas.py
│   └── services/
│       ├── ai_explanation.py
│       └── investigation.py
├── data/
│   ├── gateway.csv
│   ├── bank.csv
│   └── ledger.csv
├── frontend/
├── scripts/
├── tests/
├── generate_data.py
├── requirements.txt
├── .env.example
└── README.md
```
The accompanying ZIP contains the complete codebase, mock data, tests and configuration.
## Limitations
- Gateway, Bank and Ledger data is mock data.
- No real financial institution APIs are connected.
- Investigation rules cover the implemented scenarios.
- AI explanations require a configured LLM provider.

#Live Link - https://settlement-q-a-agent-for-fintech-su.vercel.app/
