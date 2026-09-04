# SettleTrace — Settlement Q&A Agent

An internal fintech support tool for investigating settlement records across Gateway, Bank, and Ledger data. The deterministic reconciliation engine decides the settlement result; the optional LLM layer only turns that verified result into a concise support explanation.

## Architecture

`React UI → FastAPI → deterministic investigation → PostgreSQL (Gateway / Bank / Ledger)`

The AI explanation endpoint receives the structured investigation result only. It does not access the database or determine root cause.

## Stack

- Python 3.11+ (tested with the project's requirements)
- FastAPI, SQLAlchemy, PostgreSQL, pytest
- React and Vite
- An OpenAI-compatible client for optional explanations

## Backend setup

PostgreSQL must be running and accessible. The default local database URL is `postgresql+psycopg://postgres:postgres@localhost:5432/payment_settlement`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Set this only when your PostgreSQL credentials differ from the default.
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/payment_settlement"

python generate_data.py
python scripts/init_db.py
python scripts/import_csv.py
uvicorn app.api:app --reload --port 8000
```

The generator is deterministic and writes `data/gateway.csv`, `data/bank.csv`, and `data/ledger.csv`. Running it again regenerates the mock dataset; it does not need manual CSV edits.

## Optional AI explanation

Set these variables in the shell that starts FastAPI. The application does not load `.env` files automatically.

```powershell
$env:LLM_API_KEY = "your-provider-key"
$env:LLM_MODEL = "gpt-4o-mini"              # optional
$env:LLM_BASE_URL = "https://provider/v1"   # optional, OpenAI-compatible providers
```

Without `LLM_API_KEY`, deterministic investigation endpoints still work. The explanation endpoint responds with a safe configuration error.

## Frontend setup

In a second terminal:

```powershell
cd frontend
npm install
$env:VITE_API_BASE_URL = "http://localhost:8000"  # optional; this is the default
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`). CORS is configured for the local Vite origin.

## Tests and build

```powershell
# From the repository root, with the virtual environment active
python -m pytest -q

# From frontend
npm run build
```

Tests use SQLite and mocked LLM calls; they require neither PostgreSQL nor a real LLM key/network connection.

## API

- `GET /health`
- `GET /transactions/{transaction_id}`
- `GET /investigations/{transaction_id}`
- `POST /investigations/{transaction_id}/explanation`

## Demo transactions

| Transaction | Scenario |
| --- | --- |
| `TXN-DEMO-001` | Normal Settlement |
| `TXN-DEMO-002` | Bank Delay |
| `TXN-DEMO-003` | Missing Bank Record |
| `TXN-DEMO-004` | Amount Mismatch |
| `TXN-DEMO-005` | Missing Ledger |
| `TXN-DEMO-006` | Settlement Not Initiated |
| `TXN-DEMO-007` | Duplicate Settlement |

For a reliable demo: start with `TXN-DEMO-001`, then show `TXN-DEMO-004`, `TXN-DEMO-003`, and `TXN-DEMO-007`. Generate an AI explanation only after showing the deterministic investigation result.
