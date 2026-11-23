# AI Commerce Support Backend

FastAPI service for authentication, customer and support operations, orders,
products, tickets, dashboard summaries, and AI-assisted support workflows.

## Contents

- [Technology and layout](#technology-and-layout)
- [Prerequisites](#prerequisites)
- [Install and configure](#install-and-configure)
- [Run and verify](#run-and-verify)
- [Database initialization and sample data](#database-initialization-and-sample-data)
- [Swagger and authentication](#swagger-and-authentication)
- [API reference](#api-reference)
- [Troubleshooting](#troubleshooting)

## Technology and layout

- Python with FastAPI and Uvicorn
- SQLAlchemy ORM
- SQLite by default
- Pydantic request models and settings
- JWT bearer authentication; Passlib/bcrypt password hashing
- Ollama-backed AI workflows

Important backend files and directories:

| Path | Responsibility |
|---|---|
| `app/main.py` | Creates the FastAPI application, initializes database tables and ticket-number migration, configures CORS, and mounts routers. |
| `app/api/` | Route handlers for health, authentication, products, orders, tickets, dashboards, customers, and Copilot. |
| `app/schemas/` | Pydantic request and response data models. |
| `app/models/` | SQLAlchemy database models. |
| `app/database/` | Engine/session setup, table initialization, and ticket-number migration. |
| `app/agents/` | Copilot orchestration and support/product/order AI tools. |
| `app/services/` | Business services, including order checkout and Ollama integration. |
| `seed_users.py` | Adds the sample customer and support users if they are absent. |
| `seed_prodcuts.py` | Adds sample product catalog rows. The filename is spelled `prodcuts`. |
| `seed_orders_and_tickets.py` | Adds sample orders and tickets for the seeded accounts. |
| `tests/` | Pytest coverage for API/business behavior. |

## Prerequisites

- Python 3.13 was used to verify this repository. No Python version is pinned
  by the project; use a Python version compatible with the packages in
  `requirements.txt`.
- `pip`
- Ollama installed and running for AI features, with model `llama3.2:1b`
  available.
- The `ollama` Python client is imported by the application but is not listed
  in `requirements.txt`. Install it separately as described below or update
  the dependency manifest before relying on a clean environment.

SQLite is the default database, so no separate database server is required for
local development.

## Install and configure

From the repository root, clone the repository if needed, then create the
environment from the backend directory.

### Windows PowerShell

```powershell
Set-Location .\backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install ollama
```

### macOS/Linux shell

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install ollama
```

Create `backend/.env` (or set the values in the process environment). Use a
private, randomly generated secret; do not commit real credentials.

```dotenv
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
DATABASE_URL=sqlite:///./commerce.db
```

Generate a secret locally, for example:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

```sh
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

### Configuration variables

| Variable | Required | Default | Description |
|---|---:|---|---|
| `JWT_SECRET_KEY` | Yes | None | Signs and verifies access tokens. Keep private and use a strong value. |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm. |
| `JWT_EXPIRE_MINUTES` | No | `60` | Access token lifetime in minutes. |
| `DATABASE_URL` | No | `sqlite:///./commerce.db` | SQLAlchemy database URL. With the default, the SQLite file is relative to the backend process working directory. |
| `APP_NAME` | No | `AI Commerce Support` | Settings value; the FastAPI title is currently hard-coded to the same value in `app/main.py`. |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Declared setting, but not currently used by the app. CORS origins are hard-coded to `http://localhost:5173` and `http://127.0.0.1:5173`. |

Settings load `.env` relative to the current working directory. Start the
backend from `backend/` so `.env` and the default SQLite path resolve as shown.
The repository excludes local `.env` files. Create `backend/.env` for local
development, use a private random secret, and never reuse it in a deployed
environment.

The frontend uses relative `/api` URLs. Vite proxies these requests to
`http://127.0.0.1:8000` during local development. If changing the backend
host or port, update `frontend/vite.config.js`. The backend CORS allowlist
applies when a browser calls the backend directly, rather than through the
Vite proxy.

## Run and verify

Run commands from `backend/` with the virtual environment activated.

```powershell
python -m uvicorn app.main:app --reload
```

The default development server is `http://127.0.0.1:8000`. Uvicorn prints a
startup message after the application imports and starts.

Verify the service:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Expected response:

```json
{"status":"ok"}
```

OpenAPI and Swagger UI:

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

The project provides a development command, not a separate production
configuration. For deployment, use an appropriate ASGI server/process manager,
secure secrets, configure database/CORS for the deployment, and do not enable
development reload.

## Database initialization and sample data

At application startup, `app/main.py` creates tables and runs the
ticket-number migration. The explicit initializer can also be run from
`backend/`:

```powershell
python -m app.database.init_db
```

The migration adds/backfills the `TicketNumber` column and its unique index.
Initialization does not seed users, products, orders, or tickets.

To load sample data, run these scripts in order:

```powershell
python seed_users.py
python seed_prodcuts.py
python seed_orders_and_tickets.py
```

The demo order/ticket seeder requires users `customer1` through `customer10`
and `support1`. The user seeder skips existing usernames. The product seeder
does not check for duplicates; run it only once against a fresh database.
Demo orders receive sample product line items from the available catalog, and
their totals are calculated from those items. Seeding changes database data;
back up an existing database before running seed scripts against it.

Run backend tests from `backend/`:

```powershell
python -m pytest -q
```

## Swagger and authentication

1. Start the backend and open `/docs`.
2. Expand `POST /api/auth/login` and use **Try it out**.
3. Submit a valid username and password. Copy the `access_token` from the
   response.
4. Click **Authorize**. Enter `Bearer <access_token>` if Swagger requests the
   complete bearer value, then authorize.
5. Execute protected routes. Support-only operations require a user whose
   role is `support`.

Protected endpoints use the HTTP `Authorization` bearer header:

```http
Authorization: Bearer <access_token>
```

Unauthenticated routes are marked **Public** in the reference below. Routes
marked **User** require a valid token; routes marked **Support** additionally
require the support role.

## API reference

All paths below are relative to `http://127.0.0.1:8000`; the complete API
prefix is `/api`. JSON request bodies use `Content-Type: application/json`.
Normal handler success responses use HTTP 200 unless otherwise noted.

### Health and products

#### `GET /api/health` — health check

- **Auth:** Public
- **Body:** None
- **Success:** `{"status":"ok"}`

#### `GET /api/products` — list product catalog

- **Auth:** Public
- **Body:** None
- **Success:** Array of products:

```json
[
  {
    "id": 1,
    "name": "Wireless Earbuds",
    "description": "Bluetooth earbuds with noise cancellation",
    "category": "Audio",
    "stock": 40,
    "price": 2499
  }
]
```

#### `POST /api/products/products` — create product

- **Auth:** Public
- **Body fields:** `name` (string), `description` (string), `category`
  (string), `stock` (integer), and `price` (number).
- **Example:**

```json
{
  "name": "Desk Lamp",
  "description": "Adjustable LED desk lamp",
  "category": "Home",
  "stock": 12,
  "price": 2499
}
```

- **Success:** Created product ORM object with the supplied fields and
  database-generated `id`.
- **Errors:** The route has no Pydantic request schema and indexes supplied
  JSON keys directly; missing/invalid fields are not translated into a
  documented validation response.

### Orders

#### `GET /api/orders/customer/{customer_id}` — list a customer's orders

- **Auth:** Public
- **Path parameter:** `customer_id` (integer user ID)
- **Body:** None
- **Success:** Array of `{id, order_number, status, total_amount}`.

#### `POST /api/orders/checkout` — create an order

- **Auth:** User
- **Body fields:** `items` (array of product ID and positive quantity),
  `customer_name` (string, required by schema), and `idempotency_key` (string).
- **Example:**

```json
{
  "items": [
    {"product_id": 1, "quantity": 2},
    {"product_id": 3, "quantity": 1}
  ],
  "customer_name": "customer1",
  "idempotency_key": "checkout-customer1-001"
}
```

- **Success:** Created order ORM object. The authenticated user's username is
  stored as the order customer name; the submitted `customer_name` is not used
  for ownership. Reusing an idempotency key returns the existing order.
- **Errors:** Invalid product, non-positive quantity, and insufficient stock
  raise `ValueError` in the service and are not explicitly mapped to an HTTP
  error by the route.

#### `GET /api/orders/my` — current user's orders

- **Auth:** User
- **Body:** None
- **Success:** Array of the current user's Order ORM objects.

#### `GET /api/orders/` — all orders

- **Auth:** Support
- **Body:** None
- **Success:** Array of `{id, order_number, customer_name, customer_id,
  status, total_amount}`, ordered newest ID first.

#### `GET /api/orders/customer/username/{username}` — orders by username

- **Auth:** Support
- **Path parameter:** `username` (customer username)
- **Body:** None
- **Success:** Array of `{id, order_number, status, total_amount,
  customer_name}`. Unknown username returns an empty array.

#### `GET /api/orders/number/{order_number}` — order details

- **Auth:** Support
- **Path parameter:** `order_number` (for example, `ORD-030`)
- **Body:** None
- **Success:** Order summary and line items. Product catalog details are
  `null` when the product record is no longer available.

```json
{
  "id": 30,
  "order_number": "ORD-030",
  "customer_name": "customer1",
  "customer_id": 1,
  "status": "PROCESSING",
  "total_amount": 5397,
  "items": [
    {
      "product_id": 8,
      "product_name": "Wireless Keyboard",
      "quantity": 3,
      "unit_price": 1799,
      "line_total": 5397,
      "product": {
        "id": 8,
        "name": "Wireless Keyboard",
        "description": "Wireless office keyboard",
        "category": "Keyboards & Mice",
        "current_price": 1799,
        "stock": 35
      }
    }
  ]
}
```

- **Errors:** Unknown order returns 404 `{"detail":"Order not found"}`.

### Authentication

#### `POST /api/auth/login` — obtain a bearer token

- **Auth:** Public
- **Body fields:** `username` and `password` (strings).
- **Example:**

```json
{"username":"support1","password":"your-password"}
```

- **Success:** `{"access_token":"<jwt>","token_type":"bearer","role":"support"}`
- **Errors:** Invalid credentials return 401
  `{"detail":"Invalid username or password"}`.

#### `GET /api/auth/me` — current user

- **Auth:** User
- **Body:** None
- **Success:** `{"id":1,"username":"support1","role":"support"}`

#### `GET /api/auth/support-test` — verify support access

- **Auth:** Support
- **Body:** None
- **Success:** `{"message":"Support access granted","user":"support1"}`

### Tickets

#### `POST /api/tickets/` — create a ticket

- **Auth:** User
- **Body fields:** `subject` and `description` (strings), `priority` (string,
  default `MEDIUM`), and optional `customer_id` (integer).
- **Example for a customer account:**

```json
{
  "subject": "Delivery issue",
  "description": "The package has not arrived.",
  "priority": "MEDIUM"
}
```

- **Example for support:** Include the selected customer's `customer_id`.
- **Success:** Created Ticket ORM object with an `OPEN` status and generated
  `ticket_number`.
- **Rules/errors:** A support user must provide a valid customer ID; missing
  ID returns 422 and an unknown or non-customer ID returns 404. Customer
  accounts cannot specify `customer_id`; doing so returns 403.

#### `GET /api/tickets/my` — current user's tickets

- **Auth:** User
- **Body:** None
- **Success:** Array of the current user's Ticket ORM objects.

#### `GET /api/tickets/` — all tickets

- **Auth:** Support
- **Body:** None
- **Success:** Array of Ticket ORM objects.

#### `PUT /api/tickets/{ticket_id}/status` — update ticket status

- **Auth:** Support
- **Path parameter:** `ticket_id` (integer database ID, not ticket number)
- **Body:** `status` must be `OPEN`, `IN_PROGRESS`, `RESOLVED`, or `CLOSED`.

```json
{"status":"IN_PROGRESS"}
```

- **Success:** Updated Ticket ORM object. A status-history record is added.
- **Errors:** Unknown ticket returns 404 `{"detail":"Ticket not found"}`;
  unsupported status produces request validation error 422.

#### `POST /api/tickets/{ticket_id}/messages` — add a message

- **Auth:** User
- **Path parameter:** `ticket_id` (integer database ID)
- **Body:** `{"message":"I am checking this issue."}`
- **Success:** Created TicketMessage ORM object.
- **Errors:** Unknown ticket 404; a customer who does not own the ticket 403.
  Support can access any ticket.

#### `GET /api/tickets/{ticket_id}/messages` — list conversation messages

- **Auth:** User
- **Path parameter:** `ticket_id` (integer database ID)
- **Body:** None
- **Success:** Array of `{id, username, role, message, created_at}`.
- **Errors:** Unknown ticket 404; a customer who does not own the ticket 403.

#### `GET /api/tickets/{ticket_id}/history` — ticket status history

- **Auth:** User
- **Path parameter:** `ticket_id` (integer database ID)
- **Body:** None
- **Success:** Array of TicketStatusHistory ORM objects.
- **Errors:** Unknown ticket 404; a customer who does not own the ticket 403.

#### `GET /api/tickets/customer/{customer_id}` — tickets for customer

- **Auth:** Support
- **Path parameter:** `customer_id` (integer user ID)
- **Body:** None
- **Success:** Array of `{ticket_number, subject, status, description,
  priority}`. The returned priority is computed as `HIGH` for `OPEN` tickets
  and `LOW` for other statuses.

### Dashboards

#### `GET /api/dashboard/customer` — customer dashboard

- **Auth:** User
- **Body:** None
- **Success:** Example:

```json
{
  "username": "customer1",
  "orders": 3,
  "open_tickets": 1,
  "resolved_tickets": 2
}
```

#### `GET /api/dashboard/support` — support dashboard summary

- **Auth:** Support
- **Body:** None
- **Success:** `{"metrics":{"total_orders":30,"total_tickets":20,
  "open_tickets":3,"in_progress_tickets":9,"resolved_tickets":8},
  "recent_tickets":[...]}`
- `recent_tickets` contains Ticket ORM objects.

#### `GET /api/dashboard/overview` — support operations overview

- **Auth:** Support
- **Body:** None
- **Success:** Object containing `total_orders`, `total_tickets`,
  `ticket_status_counts`, `order_status_counts`, `attention_tickets`,
  `recent_activity`, `recent_orders`, and `ticket_activity_trend`. The trend
  contains current/prior seven-day activity totals, percent change, and seven
  daily counts. The activity is based on ticket messages and status changes;
  orders do not currently have creation timestamps for an order trend.

### Copilot

#### `POST /api/copilot` — general Copilot request

- **Auth:** Support
- **Body fields:** Optional integer `customer_id` and `ticket_id`, plus
  required string `question`.

```json
{
  "customer_id": 1,
  "ticket_id": 1,
  "question": "What should I tell the customer?"
}
```

- **Success:** `{"response":...}`; the response shape depends on the
  question and available customer/ticket data.

#### `POST /api/copilot/insights` — ticket insight summary

- **Auth:** Support
- **Body:** `{"ticket_number":"TKT-001"}`
- **Success:** Object containing `ticket_summary`, `executive_summary`,
  `customer_360`, `next_action`, and `draft_response`. Ticket number is
  trimmed and uppercased before lookup. AI-generated fields require Ollama.
- **Errors:** Unknown ticket returns 404 `{"detail":"Ticket not found"}`.

#### `POST /api/copilot/assistant` — AI assistant feature

- **Auth:** Support
- **Body fields:** Required `feature` and `question`; optional `customer_id`,
  `ticket_id`, and `order_id` are integers or null.

```json
{
  "feature": "order_lookup",
  "customer_id": 1,
  "ticket_id": null,
  "order_id": null,
  "question": "What is the status of the latest order?"
}
```

- **Success:** Feature-dependent object such as `{"answer":"..."}`,
  `{"recommendation":"..."}`, or `{"ticket_preview":{"subject":"...","description":"...","priority":"MEDIUM"}}`.
- **Unsupported feature:** `{"message":"Feature not implemented."}`.
- AI features require the configured Ollama service and model.

### Customers

#### `POST /api/customer/search` — find username

- **Auth:** Public
- **Body:** `{"search":"customer1"}`; `search` is a username substring.
- **Success:** First match, e.g.
  `{"customer_id":1,"username":"customer1","role":"customer"}`.
- **No match:** `{"error":"Customer not found"}`; this is returned as a normal
  response rather than an HTTP 404.

#### `GET /api/customer/` — list customer accounts and counts

- **Auth:** Support
- **Body:** None
- **Success:** Array of
  `{customer_id, username, role, total_orders, total_tickets, open_tickets}`.

### Common errors and response caveats

- Protected routes require a bearer token; invalid/missing credentials are
  rejected with 401. Support-only routes reject other roles with 403.
- Invalid Pydantic request bodies normally return 422.
- Ticket/order not-found handlers return 404 where noted above.
- Several routes return SQLAlchemy ORM objects without an explicit response
  schema. Their serialized fields are not a separately defined stable API
  contract.
- Product creation's direct key access and checkout service `ValueError`s are
  not explicitly mapped to clean API error responses.

## Troubleshooting

| Symptom | Resolution |
|---|---|
| `JWT_SECRET_KEY` missing during startup | Create `backend/.env` or set the variable in the shell. Start the command from `backend/` so the dotenv path is correct. |
| `No module named 'ollama'` during import | Install the missing client with `python -m pip install ollama`. It is imported by Copilot code but absent from `requirements.txt`. |
| AI request fails although API starts | Ensure Ollama is running and `llama3.2:1b` is available locally. |
| SQLite database appears in an unexpected folder | `sqlite:///./commerce.db` is relative to the current working directory; run from `backend/` or set an absolute `DATABASE_URL`. |
| Frontend request fails with CORS | Use the Vite development server and its `/api` proxy. For direct browser-to-backend requests, the backend CORS allowlist is configured in `app/main.py`; `CORS_ORIGINS` alone does not change it. |
| Address/port is already in use | Start Uvicorn on another port with `python -m uvicorn app.main:app --reload --port 8001` and update the `/api` proxy target in `frontend/vite.config.js`. |
| Missing demo users when running order/ticket seeder | Run `seed_users.py` first. |
| Duplicate products after reseeding | The product seeder does not deduplicate. Use a fresh database or remove duplicates through a controlled data migration; do not rerun casually. |
| Ticket number missing or legacy schema | Run `python -m app.database.init_db` from `backend/`; startup also runs the ticket-number migration. |
