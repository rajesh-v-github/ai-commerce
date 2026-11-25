# Storefront Web App, Executive Admin & Support Workflow Enhancements — 2026-11-24

## Summary

Today's release transforms the platform into **SoranoGear** *(powered by SoranoTech)* — an integrated commerce, executive operations, and AI customer support suite sharing a single FastAPI backend, authentication layer, and SQLite/PostgreSQL schema:

1. **Customer-Facing Storefront Web App (`/`)** for public guests, registered customers, and support executives.
2. **Executive-Only Admin Command Center (`/admin`)** with real-time KPIs, inventory watchlists, auto-serialized SKUs, multi-tone AI product copywriting, order fulfillment workflows, and Customer 360° CRM.
3. **Enhanced Backend & Support Executive Workspace (`/support`)** with refined AI Copilot product lookup/recommendation accuracy, resilient offline fallbacks, sequential order numbering, non-destructive Alembic migrations, and proxy-safe authentication.

No database files, `.env` secrets, or credentials are committed to the repository.

---

## What Changed

### 1. SoranoGear Customer Storefront Web App (`/`)

- **Unified Storefront Experience (`frontend/src/storefront/`, `backend/app/api/store.py`):**
  - Built responsive catalog browsing across 10 electronics & hardware categories (`Audio`, `Accessories`, `Cameras`, `Displays`, `Gaming`, `Laptops`, `Networking`, `Peripherals`, `Storage`, `Wearables`) with keyword search, brand/price/stock filters, and sorting.
  - Added curated studio product photography and matching SVG renders (`frontend/public/product-images/`) with automatic fallback handling.
  - Built Product Detail pages (`/product/:productId`) displaying live stock status, technical specifications, target audience, brand/SKU metadata, and related products.
  - Fixed top-bar category tab navigation (`StorefrontLayout.jsx`) so switching categories from any route updates URL query parameters cleanly.
- **Persistent Cart & Safe POC Mock Checkout (`/cart`, `/checkout`, `/order-confirmation/:orderNumber`):**
  - Implemented `CartProvider` supporting guest `localStorage` persistence and authenticated server-side cart sync (`/api/store/cart`) with live stock & INR pricing validation (`₹1,999` free-shipping threshold and GST breakdown).
  - Implemented transactional, idempotent POC checkout (`MOCK_CARD`, `MOCK_UPI`, `MOCK_COD`) with atomic conditional stock locking (`SELECT ... FOR UPDATE` + guarded `UPDATE ... WHERE stock >= qty`) and repeat-customer email deduplication.
- **Customer Accounts & Order Tracking (`/login`, `/register`, `/my-orders`):**
  - Added self-service customer registration (`role="customer"` strictly enforced), profile management (`GET/PUT /api/auth/me`), and itemized order history with fulfillment status timelines (`GET /api/orders/my`).

### 2. Executive-Only Admin Command Center (`/admin`)

- **Strict Role-Based Access Control (`RequireExecutive.jsx`, `backend/app/api/admin.py`):**
  - Protected all `/admin/*` frontend views and `/api/admin/*` endpoints so only authenticated Support Executives (`role="support"`) gain access; customers receive an explicit `403 Forbidden` response.
- **Executive Overview & Interactive Inventory Watchlist (`AdminOverviewSection.jsx`, `AdminLayout.jsx`):**
  - Added real-time KPIs (Revenue, Orders, Customers, Products), 7D/14D/30D revenue & order trends, category sales, and best-selling products.
  - Made every **Inventory Restock Watchlist** item clickable, deep-linking directly to `/admin/products?edit=<product_id>` and opening that product's Edit & Stock modal automatically.
  - Added contextual hover tooltip on the sidebar **Orders** badge clarifying active open pipeline orders (`PROCESSING`, `CONFIRMED`, `SHIPPED`) vs. total historical orders.
- **Product & Inventory Management with Auto-Serialized SKUs (`AdminProductsSection.jsx`, `product_service.py`):**
  - Built full Product CRUD, inline stock/threshold adjustment (`PATCH /api/admin/products/{id}/inventory`), validated image file uploads (`.jpg`, `.jpeg`, `.png`, `.webp`, `.svg`), and order-safe soft deactivation when deleting products referenced in historical orders.
  - Standardized SKUs on `SG-<CAT>-<NNN>` (e.g., `SG-AUD-001` through `SG-MON-015`, next `016+`), auto-generated dynamically from Category/Product Name and the last global product serial number, with a non-editable SKU field in Add/Edit Product modals.
- **Multi-Tone AI Product Copywriter (`ollama_service.py`, `AdminProductsSection.jsx`):**
  - Added **"Generate Description with AI"** supporting 4 distinct tones (`Balanced`, `Concise`, `Premium`, `Technical`).
  - Uses local Ollama (`llama3.2:1b`) when running, optional OpenAI-compatible HTTP fallback when configured, and a built-in grounded copywriter fallback (`sorano-copywriter-v1`) when Ollama is offline—producing distinct, attribute-grounded copy across regenerations without fabricating unsupported specs.
- **Live Order Fulfillment & Customer 360° CRM (`AdminOrdersSection.jsx`, `AdminCustomersSection.jsx`):**
  - Added 10-second live incoming order polling, status/payment updates (`PROCESSING`, `CONFIRMED`, `SHIPPED`, `DELIVERED`, `CANCELLED`), automatic stock restoration on order cancellation, `OrderStatusHistory` audit trails, and Customer 360° profiles combining orders, tickets, and lifetime spend.

### 3. Backend & Support Executive Workspace (`/support`) Enhancements

- **Sequential Serial Order Numbering (`backend/app/services/order_service.py`):**
  - Updated new order number generation from random hex suffixes to zero-padded sequential serial numbers (`ORD-<YYYYMMDD>-<NNNN>`, e.g., `ORD-20261124-0031`, `ORD-20261124-0032`, `ORD-20261124-0033`), while preserving legacy `ORD-001`–`ORD-030` identifiers.
- **Support Copilot Product Lookup & Recommendations (`backend/app/agents/tools.py`):**
  - Improved pre-filtering, category/device-type disambiguation, exclusion rules (e.g., separating wireless audio from wireless mice/keyboards, and gaming laptops from gaming accessories), budget parsing (`under ₹X`), Ollama prompt grounding, post-LLM response validation, and deterministic catalog fallbacks when Ollama is offline.
  - Added graceful offline fallbacks for Support Copilot Order Lookup and Ticket Summary when local Ollama is unavailable.
- **Database Migration, Seeding & Executive Provisioning:**
  - Added non-destructive cross-dialect Alembic revision `8f3c91a4b201_ecommerce_storefront_and_admin_extensions.py` supporting both SQLite and PostgreSQL.
  - Added `backend/provision_executive.py` CLI to create or promote `support` executive accounts securely without public registration endpoints.
  - Enhanced `backend/seed_orders_and_tickets.py` to populate realistic `OrderItem` line items for demo orders missing items.
- **Proxy & Embedded Browser Auth Resilience (`apiClient.js`, `authStorage.js`, `dependencies.py`):**
  - Added `X-Auth-Token` header support alongside standard `Authorization: Bearer` tokens and safe in-memory fallback when browser `localStorage` is restricted.

---

## Verification Summary

- **Backend Automated Test Suite (`pytest -v`):** **58 passed** (covering storefront catalog, cart validation, checkout idempotency & concurrency, sequential order numbers, RBAC guards, admin dashboard KPIs, serial SKU generation, multi-tone AI copywriting + offline fallbacks, Support Copilot relevance prompts, demo seeding, and SQLite/PostgreSQL migrations).
- **Frontend Static Analysis & Production Bundle:**
  - `npm run lint` — **0 errors, 0 warnings**
  - `npm run build` — **Succeeded cleanly**
- **Live End-to-End Checks:** Verified Storefront browsing & POC checkout, `/admin` KPIs, clickable watchlist restock editing, read-only serial SKU generation, multi-tone AI description generation, sequential `ORD-YYYYMMDD-NNNN` order numbers, and `/support` Copilot lookups.
