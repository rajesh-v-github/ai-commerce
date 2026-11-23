# AI Commerce Support

AI Commerce Support is a full-stack customer-support workspace with a React
frontend and a FastAPI backend. It includes a support dashboard, orders,
products, tickets, customer records, and AI-assisted support workflows.

## Project layout

- `backend/` — FastAPI API, database models, seed scripts, and tests. See
  [backend setup and API documentation](backend/README.md).
- `frontend/` — React and Vite support workspace.
- `TEMPORARY-SHARING.md` — Windows instructions for sharing a local demo
  temporarily through LocalTunnel.

## Run locally (Windows)

### Prerequisites

- Python 3.13 (or a compatible Python version) and pip.
- Node.js and npm. See [frontend/README.md](frontend/README.md) for the Vite
  Node.js version requirement.
- Ollama for AI features. Download the installer for Windows, macOS, or Linux
  from the [official Ollama download page](https://ollama.com/download).

SQLite is included with Python through its `sqlite3` module. **You do not need
to install a separate SQLite server or database driver.**

### 1. Set up the backend

From the repository root in PowerShell:

```powershell
py -3.13 -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
Set-Location .\backend
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item ..\.env.example .env
```

Edit `backend/.env` and set `JWT_SECRET_KEY` to a private random value. Generate
one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The default `DATABASE_URL=sqlite:///./commerce.db` uses a local file at
`backend/commerce.db` when commands run from `backend/`. Initialize the schema:

```powershell
python -m app.database.init_db
```

The app also initializes tables on startup. The database file is created
locally and is intentionally excluded from Git. To use another SQLite file,
change `DATABASE_URL` in `backend/.env`; for example,
`sqlite:///./data/commerce.db` uses `backend/data/commerce.db`. Create the
`data` folder first—SQLite does not create missing parent folders.

### 2. Install Ollama and its model

Install the Ollama application from the
[official download page](https://ollama.com/download), then open/start Ollama.
The Python package that connects the backend to Ollama is installed from
`requirements.txt`; the Ollama application and model are separate downloads.

In PowerShell, download the model used by this project and test it:

```powershell
ollama --version
ollama pull llama3.2:1b
ollama run llama3.2:1b
```

Enter a prompt and type `/bye` to exit. Keep Ollama running while using AI
features; the local service normally listens on `http://127.0.0.1:11434`.

### 3. Seed fictional demo data (optional)

In the backend terminal, still in `backend/`, run these once and in order:

```powershell
python seed_users.py
python seed_prodcuts.py
python seed_orders_and_tickets.py
```

These scripts create **fictional sample users, products, orders, and tickets**.
There is no real customer or order data in this project. The demo sign-in is
`support1` / `Password123!`; sample customer accounts `customer1` through
`customer10` use the same password. Only the support account can enter the
support workspace. These are public demo credentials, not private account
secrets; never reuse them or the sample setup for production.

The product seeder does not deduplicate. Do not run it a second time against
the same database unless you intend to add duplicate sample products.

### 4. Start the backend and frontend

From `backend/`, start the API:

```powershell
python -m uvicorn app.main:app --reload
```

In a second terminal, from the repository root:

```powershell
Set-Location .\frontend
npm install
npm run dev
```

Open `http://localhost:5173/`. Vite proxies `/api` requests to the backend on
`http://127.0.0.1:8000`. Check the API at
`http://127.0.0.1:8000/api/health`.

For macOS/Linux commands, API details, tests, and troubleshooting, see
[backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).

## Configuration and data safety

The real `backend/.env` is intentionally not tracked because it contains a
`JWT_SECRET_KEY`. Create it locally from the safe root `.env.example` and use
your own random secret. Local SQLite database files and generated dependencies
are also excluded by `.gitignore`. Do not commit real credentials or use the
demo setup for production data.
