import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchAdminOverview } from "../services/adminService";
import {
  formatDateTime,
  formatINR,
  formatShortDate,
  handleProductImageError,
} from "../utils/formatters";

function AdminOverviewSection() {
  const navigate = useNavigate();
  const [days, setDays] = useState(14);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadOverview = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetchAdminOverview(days);
      setData(response);
      setError("");
    } catch (err) {
      console.error(err);
      setError("Failed to load executive commerce analytics.");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    let active = true;
    const fetchOverview = async () => {
      try {
        const response = await fetchAdminOverview(days);
        if (active) {
          setData(response);
          setError("");
        }
      } catch (err) {
        console.error(err);
        if (active) {
          setError("Failed to load executive commerce analytics.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    fetchOverview();
    return () => {
      active = false;
    };
  }, [days]);

  if (loading && !data) {
    return (
      <div className="adm-card text-center py-5">
        <div className="spinner-border text-primary" role="status"></div>
        <p className="text-muted mt-2 mb-0">
          Aggregating real-time revenue, inventory, and order metrics...
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="alert alert-danger d-flex justify-content-between align-items-center">
        <span>{error || "Analytics unavailable."}</span>
        <button
          type="button"
          className="btn btn-sm btn-outline-danger"
          onClick={loadOverview}
        >
          Retry
        </button>
      </div>
    );
  }

  const {
    kpis,
    revenue_trend: revenue_trends = [],
    category_performance: category_sales = [],
    order_status_breakdown = [],
    best_selling_products = [],
    recent_orders = [],
    low_stock_products = [],
    out_of_stock_products = [],
  } = data;

  const windowRevenueTotal = revenue_trends.reduce(
    (acc, pt) => acc + Number(pt.revenue || 0),
    0,
  );
  const windowOrderTotal = revenue_trends.reduce(
    (acc, pt) => acc + Number(pt.orders ?? pt.order_count ?? 0),
    0,
  );

  const maxTrendRevenue = Math.max(
    1,
    ...revenue_trends.map((pt) => Number(pt.revenue || 0)),
  );
  const maxCategoryRevenue = Math.max(
    1,
    ...category_sales.map((c) => Number(c.revenue || 0)),
  );

  const statusBadge = (status) => {
    switch ((status || "").toUpperCase()) {
      case "DELIVERED":
        return "badge bg-success-subtle text-success";
      case "SHIPPED":
        return "badge bg-info-subtle text-info-emphasis";
      case "CONFIRMED":
        return "badge bg-primary-subtle text-primary";
      case "CANCELLED":
        return "badge bg-danger-subtle text-danger";
      default:
        return "badge bg-warning-subtle text-warning-emphasis";
    }
  };

  return (
    <div className="d-grid gap-4">
      {/* Header */}
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
        <div>
          <h1 className="fs-3 fw-bold mb-1">Executive Commerce Overview</h1>
          <p className="text-muted small mb-0">
            Live revenue, inventory health, customer growth, and fulfillment
            performance from PostgreSQL / Commerce DB
          </p>
        </div>

        <div className="d-flex align-items-center gap-2">
          <div className="btn-group btn-group-sm" role="group">
            {[7, 14, 30].map((d) => (
              <button
                key={d}
                type="button"
                className={`btn ${
                  days === d ? "btn-primary" : "btn-outline-secondary"
                }`}
                onClick={() => setDays(d)}
              >
                {d}D Trend
              </button>
            ))}
          </div>
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            onClick={loadOverview}
          >
            <i className="bi bi-arrow-clockwise me-1"></i>
            Refresh
          </button>
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="adm-kpi-grid">
        <div className="adm-kpi-card">
          <div className="d-flex justify-content-between align-items-start">
            <span className="text-muted small fw-semibold">Total Revenue</span>
            <span className="badge bg-success-subtle text-success">
              <i className="bi bi-currency-rupee"></i> Gross
            </span>
          </div>
          <div className="fs-3 fw-bold mt-2">
            {formatINR(kpis.total_revenue)}
          </div>
          <div className="small text-muted mt-1">
            {days}d: <strong>{formatINR(windowRevenueTotal)}</strong> • Avg
            Order: {formatINR(kpis.average_order_value)}
          </div>
        </div>

        <div
          className="adm-kpi-card clickable"
          onClick={() => navigate("/admin/orders")}
        >
          <div className="d-flex justify-content-between align-items-start">
            <span className="text-muted small fw-semibold">Total Orders</span>
            <i className="bi bi-receipt text-primary fs-5"></i>
          </div>
          <div className="fs-3 fw-bold mt-2">{kpis.total_orders}</div>
          <div className="small text-muted mt-1">
            <strong>{kpis.active_orders}</strong> in fulfillment •{" "}
            {kpis.delivered_orders} delivered
          </div>
        </div>

        <div
          className="adm-kpi-card clickable"
          onClick={() => navigate("/admin/customers")}
        >
          <div className="d-flex justify-content-between align-items-start">
            <span className="text-muted small fw-semibold">
              Total Customers
            </span>
            <i className="bi bi-people text-indigo fs-5"></i>
          </div>
          <div className="fs-3 fw-bold mt-2">{kpis.total_customers}</div>
          <div className="small text-muted mt-1">
            <strong>{kpis.customers_with_orders}</strong> customers with orders
          </div>
        </div>

        <div
          className="adm-kpi-card clickable"
          onClick={() => navigate("/admin/products")}
        >
          <div className="d-flex justify-content-between align-items-start">
            <span className="text-muted small fw-semibold">Total Products</span>
            <i className="bi bi-box-seam text-secondary fs-5"></i>
          </div>
          <div className="fs-3 fw-bold mt-2">{kpis.total_products}</div>
          <div className="small text-muted mt-1">
            <strong>{kpis.active_products}</strong> active •{" "}
            {kpis.inactive_products} hidden
          </div>
        </div>

        <div
          className="adm-kpi-card clickable"
          onClick={() => navigate("/admin/products?stock_status=low_stock")}
        >
          <div className="d-flex justify-content-between align-items-start">
            <span className="text-muted small fw-semibold">
              Low Stock Products
            </span>
            <span className="badge bg-warning-subtle text-warning-emphasis">
              Restock Soon
            </span>
          </div>
          <div className="fs-3 fw-bold mt-2 text-warning-emphasis">
            {kpis.low_stock_count}
          </div>
          <div className="small text-muted mt-1">
            At or below configured threshold
          </div>
        </div>

        <div
          className="adm-kpi-card clickable"
          onClick={() => navigate("/admin/products?stock_status=out_of_stock")}
        >
          <div className="d-flex justify-content-between align-items-start">
            <span className="text-muted small fw-semibold">
              Out of Stock Products
            </span>
            <span className="badge bg-danger-subtle text-danger">Critical</span>
          </div>
          <div className="fs-3 fw-bold mt-2 text-danger">
            {kpis.out_of_stock_count}
          </div>
          <div className="small text-muted mt-1">
            Zero purchasable units remaining
          </div>
        </div>
      </div>

      {/* Revenue Trends + Sales Performance by Category */}
      <div className="row g-4">
        <div className="col-lg-8">
          <div className="adm-card h-100">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <div>
                <h2 className="fs-5 fw-bold mb-0">
                  Revenue &amp; Order Volume Trend ({days} Days)
                </h2>
                <p className="text-muted small mb-0">
                  Daily non-cancelled gross revenue and order count
                </p>
              </div>
              <span className="badge bg-light text-dark border">
                Peak Day: {formatINR(maxTrendRevenue)}
              </span>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: `repeat(${revenue_trends.length || 1}, minmax(0, 1fr))`,
                gap: days > 14 ? "4px" : "8px",
                alignItems: "end",
                height: "210px",
                paddingTop: "24px",
                borderBottom: "1px solid #e2e8f0",
              }}
            >
              {revenue_trends.map((pt) => {
                const count = Number(pt.orders ?? pt.order_count ?? 0);
                const heightPct = Math.max(
                  pt.revenue > 0 ? 8 : 2,
                  Math.round((pt.revenue / maxTrendRevenue) * 100),
                );
                return (
                  <div
                    key={pt.date}
                    className="d-flex flex-column align-items-center justify-content-end h-100"
                    title={`${formatShortDate(pt.date)}: ${formatINR(pt.revenue)} (${count} orders)`}
                  >
                    {count > 0 && days <= 14 && (
                      <span
                        className="text-muted mb-1"
                        style={{ fontSize: "10px", fontWeight: 600 }}
                      >
                        {count}
                      </span>
                    )}
                    <div
                      style={{
                        width: "100%",
                        maxWidth: "34px",
                        height: `${heightPct}%`,
                        background:
                          pt.revenue > 0
                            ? "linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%)"
                            : "#e2e8f0",
                        borderRadius: "6px 6px 0 0",
                        transition: "height 0.25s ease",
                      }}
                    />
                  </div>
                );
              })}
            </div>

            <div className="d-flex justify-content-between text-muted small mt-2">
              <span>
                {revenue_trends[0]
                  ? formatShortDate(revenue_trends[0].date)
                  : ""}
              </span>
              <span>
                Total in window:{" "}
                <strong>{formatINR(windowRevenueTotal)}</strong> across{" "}
                <strong>{windowOrderTotal}</strong> orders
              </span>
              <span>
                {revenue_trends.length > 0
                  ? formatShortDate(
                      revenue_trends[revenue_trends.length - 1].date,
                    )
                  : ""}
              </span>
            </div>
          </div>
        </div>

        <div className="col-lg-4">
          <div className="adm-card h-100">
            <h2 className="fs-5 fw-bold mb-1">Sales Performance by Category</h2>
            <p className="text-muted small mb-3">
              Revenue contribution and units sold
            </p>

            {category_sales.length === 0 ? (
              <p className="text-muted small">No category sales recorded yet.</p>
            ) : (
              <div className="d-grid gap-3">
                {category_sales.slice(0, 6).map((cat) => {
                  const pct = Math.round(
                    (cat.revenue / maxCategoryRevenue) * 100,
                  );
                  return (
                    <div key={cat.category}>
                      <div className="d-flex justify-content-between small mb-1">
                        <span className="fw-semibold">{cat.category}</span>
                        <span>
                          <strong>{formatINR(cat.revenue)}</strong>{" "}
                          <span className="text-muted">
                            ({cat.units_sold} u)
                          </span>
                        </span>
                      </div>
                      <div
                        className="progress"
                        style={{ height: "7px", backgroundColor: "#e2e8f0" }}
                      >
                        <div
                          className="progress-bar bg-primary"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <hr className="my-3" />
            <h3 className="fs-6 fw-bold mb-2">Order Status Mix</h3>
            <div className="d-flex flex-wrap gap-2">
              {order_status_breakdown.map((b) => (
                <span
                  key={b.status}
                  className={`${statusBadge(b.status)} px-2 py-1`}
                >
                  {b.status}: {b.count}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Best-Selling Products & Recent Orders */}
      <div className="row g-4">
        <div className="col-lg-6">
          <div className="adm-card h-100">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <div>
                <h2 className="fs-5 fw-bold mb-0">Best-Selling Products</h2>
                <p className="text-muted small mb-0">
                  Ranked by units sold &amp; gross revenue
                </p>
              </div>
              <Link
                to="/admin/products"
                className="btn btn-sm btn-outline-secondary"
              >
                Manage Catalog
              </Link>
            </div>

            <div className="table-responsive">
              <table className="table adm-table align-middle mb-0">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th className="text-end">Units Sold</th>
                    <th className="text-end">Revenue</th>
                    <th className="text-end">Stock</th>
                  </tr>
                </thead>
                <tbody>
                  {best_selling_products.map((prod) => (
                    <tr key={prod.product_id}>
                      <td>
                        <div className="d-flex align-items-center gap-2">
                          <img
                            src={prod.image_url}
                            alt={prod.name}
                            onError={handleProductImageError}
                            style={{
                              width: "44px",
                              height: "32px",
                              objectFit: "cover",
                              borderRadius: "6px",
                            }}
                          />
                          <div>
                            <div className="fw-semibold">{prod.name}</div>
                            <div className="text-muted" style={{ fontSize: "12px" }}>
                              {prod.category}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="text-end fw-bold">{prod.units_sold}</td>
                      <td className="text-end fw-semibold">
                        {formatINR(prod.revenue)}
                      </td>
                      <td className="text-end">
                        <span
                          className={`badge ${
                            (prod.current_stock ?? prod.stock ?? 0) === 0
                              ? "text-bg-danger"
                              : (prod.current_stock ?? prod.stock ?? 0) <= 5
                                ? "text-bg-warning"
                                : "bg-light text-dark border"
                          }`}
                        >
                          {prod.current_stock ?? prod.stock ?? 0}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="col-lg-6">
          <div className="adm-card h-100">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <div>
                <h2 className="fs-5 fw-bold mb-0">Recent Orders</h2>
                <p className="text-muted small mb-0">
                  Latest storefront &amp; support orders
                </p>
              </div>
              <Link
                to="/admin/orders"
                className="btn btn-sm btn-outline-primary"
              >
                All Orders
              </Link>
            </div>

            <div className="table-responsive">
              <table className="table adm-table align-middle mb-0">
                <thead>
                  <tr>
                    <th>Order #</th>
                    <th>Customer</th>
                    <th>Status</th>
                    <th className="text-end">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {recent_orders.slice(0, 7).map((ord) => (
                    <tr
                      key={ord.id}
                      style={{ cursor: "pointer" }}
                      onClick={() =>
                        navigate(
                          `/admin/orders?search=${encodeURIComponent(ord.order_number)}`,
                        )
                      }
                    >
                      <td>
                        <div className="font-monospace fw-bold">
                          {ord.order_number}
                        </div>
                        <div className="text-muted" style={{ fontSize: "11px" }}>
                          {formatDateTime(ord.created_at)}
                        </div>
                      </td>
                      <td>
                        <div className="fw-semibold">{ord.customer_name}</div>
                        <div className="text-muted" style={{ fontSize: "11px" }}>
                          {ord.item_count}{" "}
                          {ord.item_count === 1 ? "item" : "items"}
                        </div>
                      </td>
                      <td>
                        <span className={statusBadge(ord.status)}>
                          {ord.status}
                        </span>
                      </td>
                      <td className="text-end fw-bold">
                        {formatINR(ord.total_amount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Inventory Restock Watchlist */}
      {(low_stock_products.length > 0 || out_of_stock_products.length > 0) && (
        <div className="adm-card">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <div>
              <h2 className="fs-5 fw-bold mb-0">
                <i className="bi bi-exclamation-triangle-fill text-warning me-2"></i>
                Inventory Restock Watchlist
              </h2>
              <p className="text-muted small mb-0">
                Products currently depleted or approaching reorder thresholds —
                click any product card to restock &amp; edit
              </p>
            </div>
            <Link
              to="/admin/products?stock_status=low_stock"
              className="btn btn-sm btn-outline-warning text-dark"
            >
              Adjust Inventory
            </Link>
          </div>

          <div className="row g-3">
            {[...out_of_stock_products, ...low_stock_products]
              .slice(0, 6)
              .map((item) => (
                <div key={item.id} className="col-md-4">
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/admin/products?edit=${item.id}`)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        navigate(`/admin/products?edit=${item.id}`);
                      }
                    }}
                    title={`Click to restock and edit ${item.name}`}
                    className="adm-watchlist-item border rounded-3 p-3 d-flex align-items-center justify-content-between gap-2 bg-light"
                  >
                    <div className="d-flex align-items-center gap-2 min-w-0">
                      <img
                        src={item.image_url}
                        alt={item.name}
                        onError={handleProductImageError}
                        style={{
                          width: "46px",
                          height: "34px",
                          objectFit: "cover",
                          borderRadius: "6px",
                        }}
                      />
                      <div className="text-truncate">
                        <div className="fw-semibold small text-truncate">
                          {item.name}
                        </div>
                        <div className="text-muted" style={{ fontSize: "11.5px" }}>
                          Threshold: {item.low_stock_threshold} •{" "}
                          <span className="text-primary fw-medium">
                            Edit &amp; Restock
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="d-flex align-items-center gap-2 flex-shrink-0">
                      <span
                        className={`badge ${
                          item.stock === 0 ? "text-bg-danger" : "text-bg-warning"
                        }`}
                      >
                        {item.stock === 0 ? "0 left" : `${item.stock} left`}
                      </span>
                      <i
                        className="bi bi-pencil-square text-primary small"
                        aria-hidden="true"
                      ></i>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminOverviewSection;
