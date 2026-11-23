# AI Commerce Support Frontend

React application for customer-support executives to review operational
metrics, orders, products, customers, and tickets, and use AI-assisted support
tools.

## Contents

- [Technology and layout](#technology-and-layout)
- [Prerequisites](#prerequisites)
- [Install and configure](#install-and-configure)
- [Run and verify](#run-and-verify)
- [Sign in and navigate](#sign-in-and-navigate)
- [Feature guide](#feature-guide)
- [Errors and limitations](#errors-and-limitations)
- [Troubleshooting](#troubleshooting)

## Technology and layout

- React 19 with JavaScript/JSX
- Vite 8 development server and production bundler
- Bootstrap 5 and Bootstrap Icons
- Axios for HTTP requests
- ESLint for linting

Important directories:

| Path | Responsibility |
|---|---|
| `src/main.jsx` | Frontend entry point. |
| `src/App.jsx` | Login/session state and top-level page selection. |
| `src/pages/` | Login and support workspace pages. |
| `src/components/` | Dashboard, orders, products, customers, tickets, assistant results, and shared UI. |
| `src/services/` | Axios API calls to the backend. |
| `src/assets/` | Logo and loading assets. |
| `public/` | Static files served as-is. |

This frontend uses client-side component state for navigation; it does not use
a URL router.

## Prerequisites

- Node.js `^20.19.0` or `>=22.12.0` (required by the installed Vite 8
  package).
- npm.
- A running AI Commerce Support backend. Its documented setup is in
  [`../backend/README.md`](../backend/README.md).

The Vite development server proxies API requests to the local backend at
`http://127.0.0.1:8000`, avoiding cross-origin browser requests in local
development.

## Install and configure

### Windows PowerShell

```powershell
git clone https://github.com/rajesh-v-github/ai-commerce.git
Set-Location .\ai-commerce\frontend
npm install
```

### macOS/Linux shell

```sh
git clone https://github.com/rajesh-v-github/ai-commerce.git
cd ai-commerce/frontend
npm install
```

The project has a `package-lock.json`; `npm install` resolves and installs the
declared dependencies.

### Environment and backend URL

The frontend does **not** read a `.env` file and has no frontend environment
variables. API service modules use relative `/api` paths, and
`vite.config.js` proxies those requests to `http://127.0.0.1:8000` in
development. To change the backend host or port, update the Vite proxy target.

The backend must be running before signing in or loading data. The backend
uses JWT bearer authentication; after a successful login, the frontend stores
the access token and role in browser `localStorage` and attaches the token to
authenticated API requests.

## Run and verify

Start the backend separately, then run the frontend from `frontend/`.

### Development

```powershell
npm run dev
```

Vite prints the local URL, normally `http://localhost:5173/`. Open that URL
in a browser. The browser's developer console and Network panel can help
diagnose client and backend request failures.

### Production build and preview

```powershell
npm run build
npm run preview
```

The production bundle is written to `dist/`. Vite's preview server prints the
URL where the built app is available. `preview` is for local verification,
not a production hosting server.

### Lint

```powershell
npm run lint
```

Equivalent commands work in macOS/Linux shells.

## Sign in and navigate

1. Start the backend and frontend.
2. Enter a backend account's username and password in the sign-in form.
3. Click **Sign in**. On success, the support workspace opens.
4. Click **Logout** to clear the local session and return to sign-in.
5. If an authenticated request receives HTTP 401, the app shows a
   session-expired dialog; use its sign-in action to return to the login
   screen.

Invalid credentials show an alert. The frontend does not provide account
registration or user management.

The active workspace tabs are **Dashboard**, **AI Assistant**, **All Orders**,
**Products**, **Tickets**, and **Customers**. **Orders By Customer** is
currently commented out and is not an active screen.

## Feature guide

### Dashboard

The Dashboard provides a support-operations overview:

- KPI cards for open, in-progress, resolved, and all tickets, plus total
  orders.
- A needs-attention ticket list ordered by support priority/activity.
- Recent ticket messages and status changes.
- Seven-day support activity chart.
- Order status distribution and latest order records.

**Use it**

1. Select **Dashboard**.
2. Click **Refresh** to reload; if initial loading fails, use **Try again**.
3. Click an Open, In-progress, or Resolved KPI to open Tickets filtered by
   that status. Click **All tickets** to open the unfiltered ticket list.
4. Click a ticket number or **Review** in activity/attention lists to open
   that ticket in AI Assistant's Ticket Summary feature.
5. Click an order number to open the selected order's detail view in
   **All Orders**. Click the order KPI or **View all** to open the full order
   list.

**API:** `GET /api/dashboard/overview` (support role required).

The activity trend counts ticket messages and status changes, not newly
created tickets. Order creation timestamps are not stored, so order trends
are not shown.

### AI Assistant

Select one of the five assistant cards. Switching features clears the current
question and response.

#### Order Lookup

1. Select a customer.
2. Enter a question about that customer's orders, such as
   `What is the status of the latest order?`
3. Click **Look Up Orders**. Use **Clear** to reset the customer, question,
   result, and error.

A customer and nonblank question are required. Results are formatted into
order cards when the response contains recognized order details; otherwise
the answer is shown as text.

**APIs:** `GET /api/customer/` to populate the selector, then
`POST /api/copilot/assistant` with `feature: "order_lookup"`, `customer_id`,
and `question`.

#### Product Lookup

1. Enter a question, for example `Which wireless products are in stock?`
2. Click **Search Products**. Use **Clear** to reset.

A nonblank question is required. Recognized product responses are displayed
as product cards; other responses appear as text.

**API:** `POST /api/copilot/assistant` with `feature: "product_lookup"` and
`question`.

#### Product Recommendations

1. Enter customer requirements, for example
   `Recommend a lightweight laptop for travel under ₹50,000.`
2. Click **Get Recommendations**. Use **Clear** to reset.

A nonblank requirement is required. Recommendations are formatted as cards
when the response is recognizable.

**API:** `POST /api/copilot/assistant` with
`feature: "product_recommendation"` and `question`.

#### Ticket Summary

1. Choose **Ticket Summary**.
2. Enter a formatted ticket number such as `TKT-001`.
3. Click **Analyze Ticket**. Click **Clear** to remove the number and current
   summary.

The results can include a ticket overview, customer metrics and latest order,
status timeline, executive summary, recommended action, conversation history,
and AI draft response. Use **Copy Response** in the draft-response card to
copy the response.

**API:** `POST /api/copilot/insights` with `{"ticket_number":"TKT-001"}`.
The backend resolves the public ticket number to the internal ticket ID.

The frontend does not block an empty ticket-number field before submission;
the API reports a missing/invalid ticket. A request failure is shown as a
browser alert.

#### Create Ticket

1. Choose **Create Ticket** and select the customer the ticket concerns.
2. Describe the customer's issue, what happened, and troubleshooting already
   attempted.
3. Click **Generate Ticket Draft**.
4. Review and edit the generated subject and description; choose priority
   `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.
5. Click **Create Ticket** to persist the ticket, or **Discard draft** to
   cancel.

The customer and a nonblank issue description are required before generating
a draft. The subject and description must remain nonblank to enable ticket
creation. A successful response displays the generated ticket number and
refreshes dashboard data.

**APIs:** `GET /api/customer/`; `POST /api/copilot/assistant` with
`feature: "create_ticket"` and the customer issue; then `POST /api/tickets/`
with the reviewed subject, description, priority, and selected `customer_id`.

The create API assigns support-created tickets to the explicitly selected
customer.

### All Orders

1. Use the search field to filter by order number or customer name as you
   type; click **Search** to apply the text.
2. Click an order number to open the focused order-details view.
3. Review its customer, status, order total, product items, quantities,
   purchase-time unit prices, line totals, and available product catalog
   description/category/current price/stock.
4. Click **Back to all orders** to return to the list and restore search.

**APIs:** `GET /api/orders/` and, for the selected order,
`GET /api/orders/number/{order_number}`. Both require support authentication.

Product catalog information is not available if an ordered product no longer
has a matching catalog record; the saved order item details remain visible.
Order list filtering is client-side.

### Products

1. Open **Products**.
2. Enter a product name; results filter as you type. Click **Search** to
   apply the text.
3. Review product ID, name, category, price, and stock.

**API:** `GET /api/products`. Search is client-side. Product-fetch failures
are logged but do not have a dedicated visible error panel.

### Tickets

1. Open **Tickets** to see ticket number, subject, and status.
2. Enter a ticket number such as `TKT-001`; results filter as you type.
   Click **Search** to apply the text.
3. If opened from a Dashboard status KPI, the status filter is shown and the
   ticket-number search is hidden. Click **Clear filter** to remove the
   status filter and restore search.

**API:** `GET /api/tickets/` (support role required). Both the search and
status filter are applied client-side. The table currently has no ticket
detail, message, or status-edit action.

### Customers

1. Open **Customers**.
2. Search by username and press Enter or click **Search**.
3. Review customer ID, username, order count, ticket count, and open-ticket
   count.

**API:** `GET /api/customer/` (support role required). Search is client-side.
If there are no matches for a search, a warning is shown and the full
customer list remains displayed.

## Errors and limitations

- Dashboard load errors have a visible message and retry action.
- AI Assistant errors appear inline, except Ticket Summary failures, which
  use a browser alert.
- Order detail loading and errors are shown in the detail view.
- Ticket, product, customer, and all-orders list fetch failures are logged
  to the console and do not have dedicated visible error states.
- The frontend currently has no registration/user-management, product
  editing, checkout, ticket status-editing, or ticket conversation workflow.
  Such backend APIs, where present, are not exposed as active UI workflows.
- The frontend does not configure or manage the Ollama installation/model.
  AI feature availability depends on the backend's Ollama setup.

## Troubleshooting

| Symptom | Resolution |
|---|---|
| `npm install` or Vite reports an unsupported Node version | Use Node.js `^20.19.0` or `>=22.12.0`, then run `npm install` again. |
| Page loads but API requests fail | Start the backend and verify `http://127.0.0.1:8000/api/health`. |
| Browser reports CORS failure | Confirm the frontend is running through Vite at `http://localhost:5173` or `http://127.0.0.1:5173` and that the Vite `/api` proxy target is correct. |
| Requests go to the wrong host/port | Update the `/api` proxy target in `vite.config.js`; a frontend `.env` variable is not currently used. |
| Login works, then protected requests return 401 | The token may have expired. Sign in again; the frontend shows a session-expired prompt on 401. |
| AI tools return errors while ordinary APIs work | Check the backend's Ollama service and required model; AI calls are executed by the backend. |
| Production build fails | Check terminal diagnostics and run `npm install` with a supported Node version, then retry `npm run build`. |
| Lint errors | Run `npm run lint` and address the reported file/line diagnostics. |
