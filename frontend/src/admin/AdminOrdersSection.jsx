import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useToast } from "../context/toastContextObject";
import {
  fetchAdminOrderDetail,
  fetchAdminOrders,
  updateAdminOrderStatus,
} from "../services/adminService";
import {
  formatDateTime,
  formatINR,
  formatPaymentMethodLabel,
  handleProductImageError,
} from "../utils/formatters";

const ORDER_STATUSES = [
  "PROCESSING",
  "CONFIRMED",
  "SHIPPED",
  "DELIVERED",
  "CANCELLED",
];

const PAYMENT_STATUSES = ["PENDING", "PAID", "FAILED", "REFUNDED"];

function AdminOrdersSection() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { showToast } = useToast();

  const [orders, setOrders] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [statusFilter, setStatusFilter] = useState(
    searchParams.get("status") || "",
  );
  const [paymentFilter, setPaymentFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Order detail & status update modal
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [nextStatus, setNextStatus] = useState("PROCESSING");
  const [nextPaymentStatus, setNextPaymentStatus] = useState("PAID");
  const [statusNote, setStatusNote] = useState("");
  const [updatingStatus, setUpdatingStatus] = useState(false);

  const loadOrders = useCallback(
    async (silent = false) => {
      try {
        if (!silent) {
          setLoading(true);
        }
        const data = await fetchAdminOrders({
          search: search.trim() || undefined,
          status: statusFilter || undefined,
          payment_status: paymentFilter || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        });
        setOrders(data.orders || data.items || []);
        setTotalCount(data.total || 0);
      } catch (err) {
        console.error(err);
        if (!silent) {
          showToast("Failed to load orders.", "danger");
        }
      } finally {
        if (!silent) {
          setLoading(false);
        }
      }
    },
    [search, statusFilter, paymentFilter, dateFrom, dateTo, showToast],
  );

  useEffect(() => {
    let active = true;
    const fetchOrders = async () => {
      try {
        const data = await fetchAdminOrders({
          search: search.trim() || undefined,
          status: statusFilter || undefined,
          payment_status: paymentFilter || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        });
        if (active) {
          setOrders(data.orders || data.items || []);
          setTotalCount(data.total || 0);
        }
      } catch (err) {
        console.error(err);
        if (active) {
          showToast("Failed to load orders.", "danger");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    fetchOrders();
    return () => {
      active = false;
    };
  }, [search, statusFilter, paymentFilter, dateFrom, dateTo, showToast]);

  useEffect(() => {
    if (!autoRefresh) {
      return;
    }
    const timer = setInterval(() => {
      loadOrders(true);
    }, 10000);
    return () => clearInterval(timer);
  }, [autoRefresh, loadOrders]);

  const openOrderDetail = async (orderSummary) => {
    try {
      setLoadingDetail(true);
      setSelectedOrder(orderSummary);
      setNextStatus(orderSummary.status || "PROCESSING");
      setNextPaymentStatus(orderSummary.payment_status || "PAID");
      setStatusNote("");
      const fullOrder = await fetchAdminOrderDetail(orderSummary.id);
      setSelectedOrder(fullOrder);
      setNextStatus(fullOrder.status || "PROCESSING");
      setNextPaymentStatus(fullOrder.payment_status || "PAID");
    } catch (err) {
      console.error(err);
      showToast("Unable to load full order details.", "danger");
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleUpdateOrder = async (e) => {
    e.preventDefault();
    if (!selectedOrder) {
      return;
    }
    try {
      setUpdatingStatus(true);
      const updated = await updateAdminOrderStatus(selectedOrder.id, {
        status: nextStatus,
        payment_status: nextPaymentStatus,
        note: statusNote.trim() || undefined,
      });
      setSelectedOrder(updated);
      setStatusNote("");
      showToast(
        `Order ${updated.order_number} updated to ${updated.status} (${updated.payment_status}).`,
        "success",
      );
      await loadOrders(true);
    } catch (err) {
      const detail = err.response?.data?.detail;
      showToast(
        typeof detail === "string"
          ? detail
          : "Failed to update order status.",
        "danger",
      );
    } finally {
      setUpdatingStatus(false);
    }
  };

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

  const paymentBadge = (pStatus) => {
    switch ((pStatus || "").toUpperCase()) {
      case "PAID":
        return "badge bg-success-subtle text-success";
      case "REFUNDED":
        return "badge bg-secondary-subtle text-secondary";
      case "FAILED":
        return "badge bg-danger-subtle text-danger";
      default:
        return "badge bg-warning-subtle text-warning-emphasis";
    }
  };

  return (
    <div className="d-grid gap-4">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
        <div>
          <h1 className="fs-3 fw-bold mb-1">Order Management &amp; Fulfillment</h1>
          <p className="text-muted small mb-0">
            Monitor incoming storefront orders in near real time, inspect
            items &amp; addresses, and manage fulfillment status
          </p>
        </div>

        <div className="d-flex align-items-center gap-2">
          <div className="form-check form-switch mb-0 me-2">
            <input
              id="adm-live-poll"
              type="checkbox"
              className="form-check-input"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <label className="form-check-label small" htmlFor="adm-live-poll">
              Live Feed (10s)
            </label>
          </div>
          <button
            type="button"
            className="btn btn-sm btn-outline-primary"
            onClick={() => loadOrders(false)}
          >
            <i className="bi bi-arrow-clockwise me-1"></i>
            Refresh ({totalCount})
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="adm-card">
        <div className="row g-2 align-items-end">
          <div className="col-md-4">
            <label className="form-label small fw-semibold mb-1">
              Search Order # or Customer
            </label>
            <input
              type="search"
              className="form-control form-control-sm"
              placeholder="ORD-..., customer name, email..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setSearchParams((prev) => {
                  const next = new URLSearchParams(prev);
                  if (e.target.value) {
                    next.set("search", e.target.value);
                  } else {
                    next.delete("search");
                  }
                  return next;
                });
              }}
            />
          </div>

          <div className="col-md-2">
            <label className="form-label small fw-semibold mb-1">
              Order Status
            </label>
            <select
              className="form-select form-select-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              {ORDER_STATUSES.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>
          </div>

          <div className="col-md-2">
            <label className="form-label small fw-semibold mb-1">
              Payment Status
            </label>
            <select
              className="form-select form-select-sm"
              value={paymentFilter}
              onChange={(e) => setPaymentFilter(e.target.value)}
            >
              <option value="">All Payments</option>
              {PAYMENT_STATUSES.map((ps) => (
                <option key={ps} value={ps}>
                  {ps}
                </option>
              ))}
            </select>
          </div>

          <div className="col-md-2">
            <label className="form-label small fw-semibold mb-1">
              From Date
            </label>
            <input
              type="date"
              className="form-control form-control-sm"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>

          <div className="col-md-2">
            <label className="form-label small fw-semibold mb-1">To Date</label>
            <input
              type="date"
              className="form-control form-control-sm"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Orders Table */}
      <div className="adm-card p-0 overflow-hidden">
        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border text-primary" role="status"></div>
          </div>
        ) : orders.length === 0 ? (
          <div className="text-center py-5">
            <p className="text-muted mb-2">
              No orders match your filter criteria.
            </p>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={() => {
                setSearch("");
                setStatusFilter("");
                setPaymentFilter("");
                setDateFrom("");
                setDateTo("");
                setSearchParams({});
              }}
            >
              Clear Filters
            </button>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table adm-table table-hover mb-0">
              <thead>
                <tr>
                  <th className="ps-4">Order Reference</th>
                  <th>Customer</th>
                  <th>Items</th>
                  <th>Payment (POC)</th>
                  <th>Order Status</th>
                  <th className="text-end">Total</th>
                  <th className="text-end pe-4">Manage</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id}>
                    <td className="ps-4">
                      <div className="font-monospace fw-bold">
                        {order.order_number}
                      </div>
                      <div className="text-muted" style={{ fontSize: "12px" }}>
                        {formatDateTime(order.created_at)}
                      </div>
                    </td>
                    <td>
                      <div className="fw-semibold">
                        {order.shipping_full_name || order.customer_name}
                      </div>
                      <div className="text-muted" style={{ fontSize: "12px" }}>
                        {order.shipping_email || order.customer_name || "—"}
                      </div>
                    </td>
                    <td>
                      <span className="badge bg-light text-dark border">
                        {order.item_count}{" "}
                        {order.item_count === 1 ? "item" : "items"}
                      </span>
                    </td>
                    <td>
                      <div>
                        <span className={paymentBadge(order.payment_status)}>
                          {order.payment_status}
                        </span>
                      </div>
                      <div className="text-muted" style={{ fontSize: "11px" }}>
                        {formatPaymentMethodLabel(order.payment_method)}
                      </div>
                    </td>
                    <td>
                      <span className={statusBadge(order.status)}>
                        {order.status}
                      </span>
                    </td>
                    <td className="text-end fw-bold">
                      {formatINR(order.total_amount)}
                    </td>
                    <td className="text-end pe-4">
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-primary"
                        onClick={() => openOrderDetail(order)}
                      >
                        Inspect &amp; Update
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Order Detail & Fulfillment Modal */}
      {selectedOrder && (
        <div className="adm-modal-backdrop" role="dialog" aria-modal="true">
          <div className="adm-modal-dialog" style={{ maxWidth: "860px" }}>
            <div className="adm-modal-header">
              <div>
                <h2 className="fs-5 fw-bold mb-0 font-monospace">
                  Order {selectedOrder.order_number}
                </h2>
                <p className="text-muted small mb-0">
                  Placed {formatDateTime(selectedOrder.created_at)} • Customer:{" "}
                  <strong>{selectedOrder.customer_name}</strong>
                </p>
              </div>
              <button
                type="button"
                className="btn-close"
                aria-label="Close"
                onClick={() => setSelectedOrder(null)}
              />
            </div>

            <div className="adm-modal-body d-grid gap-4">
              {loadingDetail && (
                <div className="text-center py-2">
                  <span className="spinner-border spinner-border-sm text-primary me-2"></span>
                  <span className="text-muted small">
                    Loading full line items &amp; audit trail...
                  </span>
                </div>
              )}

              {/* Customer & Address Details */}
              <div className="row g-3">
                <div className="col-md-4">
                  <div className="border rounded-3 p-3 h-100 bg-light">
                    <div className="small text-muted fw-bold text-uppercase mb-1">
                      Customer Details
                    </div>
                    <div className="fw-semibold">
                      {selectedOrder.shipping_full_name ||
                        selectedOrder.customer_name}
                    </div>
                    <div className="small text-muted">
                      {selectedOrder.shipping_email ||
                        selectedOrder.customer?.email ||
                        "—"}
                    </div>
                    <div className="small text-muted">
                      {selectedOrder.shipping_phone ||
                        selectedOrder.customer?.phone ||
                        "—"}
                    </div>
                  </div>
                </div>

                <div className="col-md-4">
                  <div className="border rounded-3 p-3 h-100 bg-light">
                    <div className="small text-muted fw-bold text-uppercase mb-1">
                      Shipping Address
                    </div>
                    <div className="small">
                      {selectedOrder.shipping_address || "Not recorded"}
                    </div>
                  </div>
                </div>

                <div className="col-md-4">
                  <div className="border rounded-3 p-3 h-100 bg-light">
                    <div className="small text-muted fw-bold text-uppercase mb-1">
                      Payment Summary (POC)
                    </div>
                    <div className="small fw-semibold">
                      {formatPaymentMethodLabel(selectedOrder.payment_method)}
                    </div>
                    <div className="mt-1">
                      <span
                        className={paymentBadge(selectedOrder.payment_status)}
                      >
                        {selectedOrder.payment_status}
                      </span>
                    </div>
                    {selectedOrder.payment_reference && (
                      <div className="small font-monospace text-muted mt-1">
                        Ref: {selectedOrder.payment_reference}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Order Line Items */}
              <div>
                <h3 className="fs-6 fw-bold mb-2">Ordered Items</h3>
                <div className="border rounded-3 overflow-hidden">
                  <table className="table table-sm align-middle mb-0">
                    <thead className="table-light">
                      <tr>
                        <th className="ps-3">Product</th>
                        <th className="text-center">Qty</th>
                        <th className="text-end">Unit Price</th>
                        <th className="text-end pe-3">Line Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(selectedOrder.items || []).map((item, idx) => (
                        <tr key={`${item.product_id}-${idx}`}>
                          <td className="ps-3">
                            <div className="d-flex align-items-center gap-2 py-1">
                              <img
                                src={item.image_url}
                                alt={item.product_name}
                                onError={handleProductImageError}
                                style={{
                                  width: "44px",
                                  height: "32px",
                                  objectFit: "cover",
                                  borderRadius: "6px",
                                }}
                              />
                              <div>
                                <div className="fw-semibold small">
                                  {item.product_name}
                                </div>
                                {item.sku && (
                                  <div
                                    className="text-muted font-monospace"
                                    style={{ fontSize: "11px" }}
                                  >
                                    {item.sku}
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="text-center fw-semibold">
                            {item.quantity}
                          </td>
                          <td className="text-end small">
                            {formatINR(item.unit_price)}
                          </td>
                          <td className="text-end fw-bold pe-3">
                            {formatINR(item.line_total)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="table-light">
                      <tr>
                        <td colSpan="3" className="text-end fw-bold">
                          Order Total
                        </td>
                        <td className="text-end fw-bold pe-3 fs-6">
                          {formatINR(selectedOrder.total_amount)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              {/* Status & Payment Update Form */}
              <form
                onSubmit={handleUpdateOrder}
                className="border rounded-3 p-3 bg-light"
              >
                <h3 className="fs-6 fw-bold mb-2">
                  Update Order &amp; Payment Status
                </h3>
                {nextStatus === "CANCELLED" &&
                  selectedOrder.status !== "CANCELLED" && (
                    <div className="alert alert-warning py-2 small mb-2">
                      <i className="bi bi-arrow-counterclockwise me-1"></i>
                      Cancelling this order will automatically restore its item
                      quantities back into product inventory.
                    </div>
                  )}

                <div className="row g-2 align-items-end">
                  <div className="col-md-3">
                    <label className="form-label small fw-semibold mb-1">
                      Fulfillment Status
                    </label>
                    <select
                      className="form-select form-select-sm"
                      value={nextStatus}
                      onChange={(e) => setNextStatus(e.target.value)}
                    >
                      {ORDER_STATUSES.map((st) => (
                        <option key={st} value={st}>
                          {st}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="col-md-3">
                    <label className="form-label small fw-semibold mb-1">
                      Payment Status
                    </label>
                    <select
                      className="form-select form-select-sm"
                      value={nextPaymentStatus}
                      onChange={(e) => setNextPaymentStatus(e.target.value)}
                    >
                      {PAYMENT_STATUSES.map((ps) => (
                        <option key={ps} value={ps}>
                          {ps}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="col-md-4">
                    <label className="form-label small fw-semibold mb-1">
                      Audit Note (Optional)
                    </label>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      placeholder="Dispatched via BlueDart AWB..."
                      value={statusNote}
                      onChange={(e) => setStatusNote(e.target.value)}
                    />
                  </div>

                  <div className="col-md-2">
                    <button
                      type="submit"
                      className="btn btn-sm btn-primary w-100"
                      disabled={updatingStatus}
                    >
                      {updatingStatus ? "Updating..." : "Apply"}
                    </button>
                  </div>
                </div>
              </form>

              {/* Status History Audit Trail */}
              {selectedOrder.status_history?.length > 0 && (
                <div>
                  <h3 className="fs-6 fw-bold mb-2">Order Audit History</h3>
                  <div className="border rounded-3 p-3 small d-grid gap-2">
                    {selectedOrder.status_history.map((entry) => (
                      <div
                        key={entry.id}
                        className="d-flex flex-wrap justify-content-between gap-2 border-bottom pb-2"
                      >
                        <div>
                          <span className="fw-semibold">
                            {entry.old_status
                              ? `${entry.old_status} → ${entry.new_status}`
                              : entry.new_status}
                          </span>
                          {entry.note && (
                            <span className="text-muted ms-2">
                              — {entry.note}
                            </span>
                          )}
                        </div>
                        <span className="text-muted">
                          {entry.changed_by || entry.changed_by_name
                            ? `${entry.changed_by || entry.changed_by_name} • `
                            : ""}
                          {formatDateTime(entry.changed_at)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="adm-modal-footer">
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={() => setSelectedOrder(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminOrdersSection;
