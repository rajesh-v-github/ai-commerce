# SoranoGear — AI-Powered Commerce, Executive Admin & Customer Support Platform

**SoranoGear** *(powered by SoranoTech)* is an integrated full-stack e-commerce, executive commerce operations, and AI-powered customer support platform built on **FastAPI**, **SQLAlchemy + Alembic**, **PostgreSQL / SQLite**, **Ollama (`llama3.2:1b`)**, and **React 19 + Vite**.

All three experiences share a single unified backend, authentication system, and transactional database:

1. **SoranoGear Customer Storefront (`/`)** — Accessible to **Guests**, **Customers**, and **Support Executives**. Features hardware & electronics discovery across 10 categories, keyword search, price/brand/stock filtering, product detail pages, studio product photography with graceful image fallbacks, persistent shopping cart (`localStorage` + server sync), customer account registration & order history (`/my-orders`), and a clearly labeled **POC Mock Checkout** (`MOCK_CARD`, `MOCK_UPI`, `MOCK_COD`) with atomic stock decrement, sequential serial order numbers (`ORD-YYYYMMDD-NNNN`), and order confirmation receipts.
2. **Executive-Only Admin Command Center (`/admin`)** — Strictly restricted to authenticated **Customer Support Executives (`role="support"`)** on both frontend routes and `/api/admin/*` endpoints. Provides live database KPIs (Total Revenue, Total Orders, Customers, Products, interactive Low Stock & Out of Stock restock watchlists, 7D/14D/30D Revenue Trends, Category Sales, Best-Selling Products), full Product & Inventory CRUD with auto-serialized non-editable SKUs (`SG-<CAT>-<NNN>`), image upload/URL management, multi-tone **"Generate Description with AI"** (`Balanced`, `Concise`, `Premium`, `Technical`) powered by Ollama (`llama3.2:1b`) with built-in grounded AI fallback, near-real-time incoming Order Management & fulfillment audit trails, and Customer 360° CRM management.
3. **AI-Powered Customer Support Executive Workspace (`/support`)** — Full SoranoTech support operations workspace featuring Operational Dashboard, enhanced AI Assistant/Copilot (context-grounded Product Lookup & Budget/Category Recommendations, Order Lookup, Ticket Summary, Create Ticket with graceful offline fallbacks), Orders, Products, Tickets, and Customers.

---

## Project Layout

- `backend/` — FastAPI API, SQLAlchemy models, Alembic migrations, executive provisioning CLI, seed scripts, and Pytest suite (`58` automated tests). See **[backend/README.md](backend/README.md)**.
- `frontend/` — React 19 + Vite + React Router application hosting the SoranoGear Storefront (`/`), Executive Admin Dashboard (`/admin`), and Support Copilot Workspace (`/support`). See **[frontend/README.md](frontend/README.md)**.
- `release-notes/` — Milestone release notes:
  - **[2026-11-24 — Storefront Web App, Executive Admin & Support Workflow Enhancements](release-notes/2026-11-24-storefront-admin-and-support-enhancements.md)**
  - **[2026-11-23 — PostgreSQL Migration](release-notes/2026-11-23-postgresql-migration.md)**
- `TEMPORARY-SHARING.md` — Instructions for temporary LocalTunnel sharing.

---

## Quick Start (Local Development & VS Code)

### Prerequisites

- **Python 3.11 – 3.13** and `pip`
- **Node.js `^20.19.0` or `>=22.12.0`** and `npm`
- **Database**:
  - **SQLite** works out of the box for local development (`sqlite:///./commerce.db`).
  - **PostgreSQL** is supported natively via `psycopg` v3 (`DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname`) and preserves all existing data via non-destructive Alembic migrations.
- **Ollama** (optional / recommended for live local LLM generation): Download from [ollama.com/download](https://ollama.com/download) and pull `llama3.2:1b`. Built-in grounded fallbacks keep AI product copywriting and Support Copilot lookups functional even when Ollama is offline.

### 1. Backend Setup

**Windows PowerShell:**

```powershell
py -3.13 -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
Set-Location .\backend
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item ..\.env.example .env }
```

**macOS / Linux:**

```sh
python3 -m venv backend/.venv
source backend/.venv/bin/activate
cd backend
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
[ -f .env ] || cp ../.env.example .env
```

Ensure `backend/.env` has a strong `JWT_SECRET_KEY`:

```sh
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Apply non-destructive database migrations (works on both SQLite and existing PostgreSQL databases):

```sh
python -m app.database.init_db
```

*(Optional — fresh local demo DB only)* Seed fictional demo accounts, products, orders, and tickets:

```sh
python seed_users.py
python seed_prodcuts.py
python seed_orders_and_tickets.py
```

Or provision a dedicated Support Executive account securely on an existing database without seeding demo rows:

```sh
python provision_executive.py --username admin_exec --email exec@company.com --full-name "Lead Support Executive"
```

Start the backend API server (from `backend/`):

```sh
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Ollama Local AI Model Setup (Recommended)

```sh
ollama pull llama3.2:1b
ollama serve
```

Keep Ollama running on `http://127.0.0.1:11434` for live LLM responses in `/support` AI Copilot and `/admin/products` **"Generate Description with AI"**. If Ollama is not running, the platform automatically falls back to its built-in grounded copywriter (`sorano-copywriter-v1`) and deterministic catalog/order/ticket assistants (or an optional `AI_FALLBACK_*` OpenAI-compatible provider configured in `backend/.env`).

### 3. Frontend Setup, Build & Run

Open a second terminal:

```sh
cd frontend
npm install
npm run dev
```

For production bundle verification:

```sh
npm run lint
npm run build
```

Open **`http://localhost:5173/`**:
- **`/`** — SoranoGear Customer Storefront
- **`/admin`** — Executive-Only Admin Command Center (`support` role required)
- **`/support`** — AI Customer Support Executive Workspace (`support` role required)

### 4. Automated Tests

From `backend/` (with virtual environment activated):

```sh
pytest -v
```

### Demo Sign-In Accounts (when using `seed_users.py`)

| Account | Password | Role | Access |
|---|---|---|---|
| `support1` | `Password123!` | `support` | Storefront (`/`), Admin Dashboard (`/admin`), Support Copilot (`/support`) |
| `customer1` – `customer10` | `Password123!` | `customer` | Storefront (`/`), Cart, POC Checkout, My Orders (`/my-orders`) — blocked from `/admin` & `/support` |

> **Security & POC Note:** Demo credentials are for local testing only—never reuse them in production. Storefront checkout uses clearly labeled **POC Mock Payment** methods (`MOCK_CARD`, `MOCK_UPI`, `MOCK_COD`); no real financial transactions are processed.
