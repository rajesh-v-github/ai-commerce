# SoranoGear — AI Commerce & Customer Support Backend

FastAPI backend powering all three integrated experiences of the **SoranoGear** platform:
1. **Customer-Facing E-Commerce Storefront (`/api/store/*`, `/api/orders/my`)**
2. **Executive-Only Admin Command Center (`/api/admin/*`)**
3. **AI-Powered Customer Support Executive Workspace (`/api/dashboard/*`, `/api/tickets/*`, `/api/copilot/*`, `/api/customer/*`)**

---

## Contents

- [Architecture & Directory Layout](#architecture--directory-layout)
- [Prerequisites](#prerequisites)
- [Installation & Environment Configuration](#installation--environment-configuration)
- [Database Setup: PostgreSQL & SQLite](#database-setup-postgresql--sqlite)
- [Provisioning Support Executive Accounts](#provisioning-support-executive-accounts)
- [Ollama AI & Optional Fallback Provider](#ollama-ai--optional-fallback-provider)
- [Authentication & Role-Based Access Control (RBAC)](#authentication--role-based-access-control-rbac)
- [Key API Endpoints](#key-api-endpoints)
- [Running the Server & Automated Tests](#running-the-server--automated-tests)

---

## Architecture & Directory Layout

- **Framework:** FastAPI + Uvicorn (compatible with Python 3.11 – 3.13)
- **ORM & Migrations:** SQLAlchemy 2.x + Alembic (`2046a0fd4f04` -> `8f3c91a4b201`)
- **Databases:** PostgreSQL (`postgresql+psycopg://...`) for production/shared hosting and SQLite (`sqlite:///./commerce.db`) for zero-setup local development
- **Security:** Passlib + `bcrypt==4.0.1` password hashing, PyJWT (`python-jose`) bearer tokens, strict server-side role dependencies
- **AI Engine:** Local Ollama (`llama3.2:1b`) via `app/services/ollama_service.py` with optional OpenAI-compatible HTTP fallback

| Path | Responsibility |
|---|---|
| `app/main.py` | FastAPI app initialization, CORS middleware, `/api/uploads` static mount, router registration. |
| `app/core/` | `config.py` (environment settings), `security.py` (bcrypt + JWT), `logging.py`. |
| `app/models/` | `User`, `Product`, `Order`, `OrderItem`, `OrderStatusHistory`, `CartItem`, `Ticket`, `TicketMessage`, `TicketStatusHistory`. |
| `app/schemas/` | Pydantic v2 validation schemas (`auth`, `store`, `admin`, `order`, `product`, `ticket`, `customer`, `copilot`). |
| `app/services/` | `product_service.py` (catalog enrichment, CRUD, soft-deactivation), `order_service.py` (atomic stock locking, idempotent POC checkout, customer deduplication, status history), `ollama_service.py` (Support Copilot + grounded AI product copywriting). |
| `app/api/` | `auth.py`, `store.py`, `admin.py`, `products.py`, `orders.py`, `tickets.py`, `dashboard.py`, `copilot.py`, `customer.py`, `health.py`. |
| `migrations/` | Non-destructive cross-dialect Alembic migrations (`versions/2046a0fd4f04_...` and `versions/8f3c91a4b201_ecommerce_storefront_and_admin_extensions.py`). |
| `provision_executive.py` | Secure CLI utility to create or promote a `support` executive account without public registration. |
| `migrate_sqlite_to_postgres.py` | Guarded, hash-verified utility to migrate a SQLite backup into an empty PostgreSQL schema. |
| `tests/` | 58 automated Pytest tests covering Storefront, Cart, Checkout, Sequential Order Numbers, Concurrency/Stock guards, Orders, RBAC, Admin KPIs, Serial SKUs, AI Description generation (live & built-in grounded fallback), Migrations, and Support Copilot compatibility. |

---

## Prerequisites

- Python 3.11 – 3.13 and `pip`
- SQLite (bundled with Python) **or** PostgreSQL 14+ (`psycopg[binary]` is installed via `requirements.txt`)
- Ollama (`llama3.2:1b`) running locally for live AI features

---

## Installation & Environment Configuration

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp ../.env.example .env     # Windows PowerShell: Copy-Item ..\.env.example .env
```

### Environment Variables (`backend/.env`)

| Variable | Required | Default | Description |
|---|---:|---|---|
| `JWT_SECRET_KEY` | **Yes** | — | Secret key used to sign JWT tokens. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm. |
| `JWT_EXPIRE_MINUTES` | No | `120` | Access token expiration window in minutes. |
| `DATABASE_URL` | No | `sqlite:///./commerce.db` | SQLAlchemy URL (`sqlite:///...` or `postgresql+psycopg://...`). |
| `APP_NAME` | No | `SoranoGear Commerce & Support` | FastAPI service title. |
| `CORS_ORIGINS` | No | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed browser origins. |
| `UPLOAD_DIR` | No | `./uploads` | Directory where uploaded product images (`/api/uploads/products/*`) are saved. |
| `OLLAMA_BASE_URL` | No | `http://127.0.0.1:11434` | Local Ollama HTTP endpoint. |
| `OLLAMA_MODEL` | No | `llama3.2:1b` | Ollama model name used by Support Copilot and Admin AI Product Copywriter. |
| `AI_FALLBACK_BASE_URL` | No | `""` | Optional OpenAI-compatible base URL if local Ollama is unreachable. |
| `AI_FALLBACK_API_KEY` | No | `""` | Optional API key for fallback AI provider (never commit secrets). |
| `AI_FALLBACK_MODEL` | No | `""` | Optional model identifier for fallback AI provider. |

---

## Database Setup: PostgreSQL & SQLite

Schema updates are managed strictly through **non-destructive Alembic migrations**. Existing `users`, `products`, `orders`, `order_items`, and `tickets` records are preserved intact during `upgrade head`:

- Existing `users` gain profile fields (`full_name`, `email`, `phone`, `shipping_address`, `billing_address`, `is_active`, `created_at`).
- Existing `products` gain commerce & inventory fields (`brand`, `sku`, `low_stock_threshold`, `is_active`, `image_url`, `specifications`, `target_audience`, timestamps) and automatically receive curated brand/SKU/studio image defaults **only when missing** (never overwriting custom existing product images).
- Existing `orders` gain checkout & POC payment fields (`subtotal_amount`, `shipping_amount`, `tax_amount`, `payment_method`, `payment_status`, `payment_reference`, shipping/billing snapshots, timestamps) and backfilled `order_status_history` rows.
- New tables `order_status_history` and `cart_items` are created with foreign keys and indexes.

### Apply Migrations (PostgreSQL or SQLite)

Set `DATABASE_URL` in `backend/.env`:

```dotenv
# Option A: Existing or New PostgreSQL Database
DATABASE_URL=postgresql+psycopg://DB_USER:URL_ENCODED_PASSWORD@DB_HOST:5432/DB_NAME

# Option B: Local SQLite Database
DATABASE_URL=sqlite:///./commerce.db
```

Then run from `backend/`:

```sh
python -m app.database.init_db
```

### Copy Local SQLite Data to an Empty PostgreSQL Database (Optional)

```sh
python migrate_sqlite_to_postgres.py --source /path/to/sqlite-backup.db
```

---

## Provisioning Support Executive Accounts

Public registration (`POST /api/auth/register`) **exclusively** creates `role="customer"` accounts—there is no public endpoint to register a Support Executive.

To create or promote a Support Executive (`role="support"`) safely on any SQLite or PostgreSQL database:

```sh
cd backend
python provision_executive.py \
  --username exec_admin \
  --email exec_admin@soranotech.com \
  --full-name "Primary Support Executive"
```

*(You will be prompted securely for the password if `--password` is omitted.)*

For local demo testing on a fresh database, you can also run:

```sh
python seed_users.py
python seed_prodcuts.py
python seed_orders_and_tickets.py
```

---

## Ollama AI & Optional Fallback Provider

1. Install and start Ollama from [ollama.com/download](https://ollama.com/download).
2. Pull the project model:
   ```sh
   ollama pull llama3.2:1b
   ```
3. Both the `/support` AI Copilot and the `/admin/products` **"Generate Description with AI"** endpoint (`POST /api/admin/products/generate-description`) share `app/services/ollama_service.py`:
   - Product descriptions are strictly grounded in supplied product metadata (never fabricating unsupported specs, processor models, waterproof ratings, certifications, or warranties).
   - Generated text is returned to the executive's editable form field and is **only saved** when the executive explicitly submits the product form.
   - If Ollama is unreachable and no `AI_FALLBACK_*` provider is configured, `generate_product_description` uses the built-in attribute-grounded copywriter fallback (`sorano-copywriter-v1`) across all 4 tones (`balanced`, `concise`, `premium`, `technical`), and Support Copilot tools fall back cleanly to deterministic database-backed responses.

---

## Authentication & Role-Based Access Control (RBAC)

| Role | Permitted Capabilities | Restricted Capabilities |
|---|---|---|
| **Guest (Unauthenticated)** | Browse `/api/store/products`, categories, product details, validate cart, place guest POC checkout orders, view order confirmation with `?ref=` token, register/login. | Blocked (`401`/`403`) from `/api/orders/my`, `/api/admin/*`, and executive support endpoints. |
| **Customer (`customer`)** | Everything Guest can do + persistent server cart (`/api/store/cart`), `/api/auth/me` profile editing, authenticated checkout, own order history (`/api/orders/my`), own tickets. | Strictly blocked (`403 Forbidden`) from all `/api/admin/*` endpoints, `POST /api/products/products`, `POST /api/customer/search`, other customers' orders, and executive support dashboards. |
| **Support Executive (`support`)** | Full access to Storefront, `/api/admin/*` (Dashboard KPIs, Product/Inventory CRUD, AI Copywriter, Order Fulfillment, Customer 360 CRM), and all `/support` Copilot/Ticket/Dashboard APIs. | — |

---

## Key API Endpoints

### Storefront & Customer APIs
- `GET /api/store/products` — Browse/search/filter/sort active catalog (`q`, `category`, `brand`, `min_price`, `max_price`, `in_stock`, `sort`).
- `GET /api/store/categories` — Active categories with product counts, starting prices, and category hero images.
- `GET /api/store/products/{product_id}` — Product detail + related products.
- `POST /api/store/cart/validate` — Validate cart items against live stock and calculate INR subtotal, free-shipping threshold (`₹1,999`), included GST, and warnings.
- `GET | PUT | DELETE /api/store/cart` — Authenticated persistent cart sync.
- `POST /api/store/checkout` — Transactional, idempotent POC mock checkout (`MOCK_CARD`, `MOCK_UPI`, `MOCK_COD`) with atomic conditional stock decrement (`SELECT ... FOR UPDATE` on PostgreSQL + guarded atomic `UPDATE ... WHERE stock >= qty`) and repeat-customer email deduplication.
- `GET /api/store/orders/confirmation/{order_number}` — Order confirmation receipt (verified by owner/support JWT or `?ref=` payment reference).
- `POST /api/auth/register` — Public customer account registration (`role="customer"` enforced).
- `POST /api/auth/login` — Sign in via username or email.
- `GET | PUT /api/auth/me` — Current user profile read/update.
- `GET /api/orders/my` — Authenticated user's full order history & status timelines.

### Executive-Only Admin APIs (`role="support"` required on all routes)
- `GET /api/admin/dashboard?days=14` — Real-time KPIs, daily revenue & order trends, category sales performance, order status breakdown, best-selling products, recent orders, and low/out-of-stock alerts.
- `GET | POST /api/admin/products` — List/filter/sort all products (including inactive) and create new products.
- `PUT | DELETE /api/admin/products/{product_id}` — Edit product or delete/soft-deactivate (products referenced in historical orders are automatically soft-deactivated to preserve order integrity).
- `PATCH /api/admin/products/{product_id}/inventory` — Adjust stock quantity and low-stock alert threshold.
- `POST /api/admin/products/upload-image` — Validated image upload (`.jpg`, `.jpeg`, `.png`, `.webp`, `.svg`, up to 5 MB).
- `GET /api/admin/ai/status` — Check Ollama / fallback AI readiness.
- `POST /api/admin/products/generate-description` — Generate grounded e-commerce product description via Ollama.
- `GET /api/admin/orders` & `GET /api/admin/orders/{order_id}` — Filterable live order feed and full order detail with audit history.
- `PATCH /api/admin/orders/{order_id}/status` — Update fulfillment status (`PROCESSING`, `CONFIRMED`, `SHIPPED`, `DELIVERED`, `CANCELLED`) and payment status (`PAID`, `PENDING`, `REFUNDED`, `FAILED`), automatically restoring stock on cancellation and recording `OrderStatusHistory`.
- `GET | POST /api/admin/customers` & `GET | PUT /api/admin/customers/{customer_id}` — Customer CRM directory, creation, editing, and 360° profile (orders + tickets + lifetime spend).

### Existing Support Workspace APIs (Preserved)
- `GET /api/dashboard/overview`, `GET /api/dashboard/support`, `GET /api/dashboard/customer`
- `POST /api/copilot/assistant`, `POST /api/copilot/insights`, `POST /api/copilot`
- `GET | POST /api/tickets/`, `PUT /api/tickets/{id}/status`, `GET | POST /api/tickets/{id}/messages`, `GET /api/tickets/{id}/history`
- `GET /api/orders/`, `GET /api/orders/number/{order_number}`, `GET /api/customer/`, `POST /api/customer/search`

---

## Running the Server & Automated Tests

Start Uvicorn from `backend/`:

```sh
./.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health check: `http://127.0.0.1:8000/api/health`
- Interactive Swagger docs: `http://127.0.0.1:8000/docs`

Run the full Pytest suite (58 tests):

```sh
./.venv/bin/pytest -v
```
