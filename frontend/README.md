# SoranoGear — Storefront, Executive Admin & AI Support Frontend

Unified React 19 + Vite single-page application delivering three connected experiences on top of the SoranoGear / SoranoTech commerce backend:

1. **SoranoGear Customer Storefront (`/`)** — Public & authenticated e-commerce storefront for browsing electronics & computing gear, managing a persistent cart, completing safe POC mock checkout, and tracking orders.
2. **Executive-Only Admin Command Center (`/admin`)** — Protected executive dashboard for real-time commerce KPIs, revenue trends, product & inventory management, AI-assisted product description generation, live order fulfillment, and Customer 360° CRM.
3. **Customer Support Executive Workspace (`/support`)** — The preserved AI-powered support desk featuring Operational Dashboard, Ollama AI Copilot (Order Lookup, Product Lookup, Product Recommendations, Ticket Summary, Create Ticket), Orders, Products, Tickets, and Customers.

---

## Technology & Directory Layout

- **React 19** + **React Router (`react-router-dom`)**
- **Vite 8** dev server & bundler (configured with `/api` proxy to `http://127.0.0.1:8000`)
- **Bootstrap 5** + **Bootstrap Icons** + scoped design systems (`Storefront.css`, `Admin.css`, `CopilotPage.css`)
- **Axios** HTTP services with automatic JWT bearer injection and `401` session-expiry detection

| Path | Responsibility |
|---|---|
| `src/App.jsx` | Top-level `BrowserRouter`, context providers (`ToastProvider`, `AuthProvider`, `CartProvider`), and route table. |
| `src/context/` | Authentication state (`AuthProvider.jsx`), persistent guest/authenticated cart state (`CartProvider.jsx`), and toast notifications (`ToastProvider.jsx`). |
| `src/storefront/` | Customer Storefront UI: `StorefrontLayout`, `StoreHomePage`, `ProductCard`, `ProductDetailPage`, `CartPage`, `CheckoutPage`, `OrderConfirmationPage`, `CustomerOrdersPage`, `StoreAuthPage`. |
| `src/admin/` | Executive Admin UI: `RequireExecutive` (403/login guard), `AdminLayout` (10s live order polling + AI status), `AdminOverviewSection`, `AdminProductsSection` (with **"Generate Description with AI"**), `AdminOrdersSection`, `AdminCustomersSection`. |
| `src/pages/` & `src/components/` | Existing Customer Support Executive Workspace (`LoginPage.jsx`, `CopilotPage.jsx`, `DashboardTab`, `TicketsTab`, `OrdersTab`, `ProductsTab`, `CustomersTab`, and insight cards). |
| `src/services/` | Relative `/api/*` clients (`apiClient.js`, `authService.js`, `storeService.js`, `adminService.js`, `copilotService.js`, `dashboardService.js`, `ticketService.js`, `orderService.js`, `productService.js`, `customerService.js`). |
| `public/product-images/` | Curated studio product photos (`.jpg`), matching hardware renders (`.svg`), and `fallback-product.svg` error fallback. |

---

## Route Map & Role Access

| Route | Experience | Access Level |
|---|---|---|
| `/` | SoranoGear Storefront Home, Category Grid, Search & Filters | Public, Customer, Support Executive |
| `/product/:productId` | Product Detail, Specs, Live Stock Badge & Related Gear | Public, Customer, Support Executive |
| `/cart` | Shopping Cart, Quantity Controls & Free-Shipping Progress | Public, Customer, Support Executive |
| `/checkout` | Safe POC Mock Checkout (`MOCK_CARD`, `MOCK_UPI`, `MOCK_COD`) | Public (Guest), Customer, Support Executive |
| `/order-confirmation/:orderNumber` | Itemized Order Confirmation Receipt | Order Owner, Support Executive, or Valid `?ref=` Token |
| `/my-orders` | Customer Order History, Timelines & Editable Account Profile | Authenticated Customer or Support Executive |
| `/login` & `/register` | Customer / Executive Sign-In & Customer Account Registration | Public |
| `/support` | AI Customer Support Executive Workspace & Copilot | **Support Executive Only (`role="support"`)** |
| `/admin` | Executive Commerce Overview, KPIs & Revenue Trends | **Support Executive Only (`role="support"`)** |
| `/admin/products` | Product CRUD, Inline Stock Control, Image Upload & **AI Copywriter** | **Support Executive Only (`role="support"`)** |
| `/admin/orders` | Live Incoming Order Feed, Inspection & Status/Payment Updates | **Support Executive Only (`role="support"`)** |
| `/admin/customers` | Customer CRM Directory, Add/Edit & 360° Order/Ticket History | **Support Executive Only (`role="support"`)** |

> **Frontend + Backend RBAC Enforcement:** Unauthenticated users visiting `/admin` are redirected to `/login?redirect=/admin`. Authenticated `customer` users visiting `/admin` or `/support` receive an explicit **HTTP 403 — Executive Authorization Required** screen without firing admin API calls, and all `/api/admin/*` backend routes independently enforce `role == "support"`.

---

## Install, Run & Verify

### Prerequisites

- Node.js `^20.19.0` or `>=22.12.0` and `npm`
- Running backend API on `http://127.0.0.1:8000` (see [`../backend/README.md`](../backend/README.md))

### Development Server

```sh
cd frontend
npm install
npm run dev
```

Open `http://localhost:5714/`. All `/api/*` calls are proxied to `http://127.0.0.1:8000` by `vite.config.js` (no hardcoded `localhost` URLs in browser code).

### Lint & Production Build

```sh
npm run lint
npm run build
```
