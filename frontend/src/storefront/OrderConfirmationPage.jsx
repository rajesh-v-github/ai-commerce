import { useEffect, useState } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/authContextObject";
import { getOrderConfirmation } from "../services/storeService";
import {
  formatDateTime,
  formatINR,
  formatPaymentMethodLabel,
  handleProductImageError,
} from "../utils/formatters";

function OrderConfirmationPage() {
  const { orderNumber } = useParams();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  const [order, setOrder] = useState(() => location.state?.order || null);
  const [loading, setLoading] = useState(() => !location.state?.order);
  const [error, setError] = useState("");

  const refCode = searchParams.get("ref") || "";

  useEffect(() => {
    if (order && order.order_number === orderNumber) {
      return;
    }
    let active = true;
    const loadOrder = async () => {
      try {
        setLoading(true);
        const data = await getOrderConfirmation(orderNumber, refCode);
        if (active) {
          setOrder(data);
          setError("");
        }
      } catch (err) {
        console.error(err);
        if (active) {
          setError(
            "Order confirmation details could not be loaded. Sign in to view your orders.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    loadOrder();
    return () => {
      active = false;
    };
  }, [order, orderNumber, refCode]);

  if (loading) {
    return (
      <div className="sg-container py-5 text-center">
        <div className="spinner-border text-primary" role="status"></div>
        <p className="text-muted mt-2">Loading your order receipt...</p>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="sg-container py-5">
        <div className="sg-panel text-center py-5">
          <i
            className="bi bi-receipt text-muted"
            style={{ fontSize: "42px" }}
          ></i>
          <h1 className="fs-4 fw-bold mt-3">Order Receipt Protected</h1>
          <p className="text-muted mt-1 mb-3">{error}</p>
          <div className="d-flex justify-content-center gap-2">
            <Link to="/login" className="sg-btn-primary">
              Sign In
            </Link>
            <Link to="/" className="btn btn-outline-secondary">
              Continue Shopping
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="sg-container py-4 mb-5">
      <div className="sg-panel mb-4 text-center py-4">
        <span
          className="d-inline-grid rounded-circle bg-success-subtle text-success mb-3"
          style={{ width: "64px", height: "64px", placeItems: "center", fontSize: "30px" }}
        >
          <i className="bi bi-check-lg"></i>
        </span>
        <p className="text-uppercase small fw-bold text-success mb-1">
          Order Confirmed
        </p>
        <h1 className="fs-2 fw-bold mb-2">
          Thank you, {order.shipping_full_name || order.customer_name}!
        </h1>
        <p className="text-muted mb-3">
          Your order reference is{" "}
          <strong className="text-dark font-monospace">
            {order.order_number}
          </strong>{" "}
          • Placed on {formatDateTime(order.created_at)}
        </p>
        <div className="d-flex flex-wrap justify-content-center gap-2">
          <span className="badge text-bg-primary px-3 py-2">
            Order Status: {order.status}
          </span>
          <span className="badge text-bg-secondary px-3 py-2">
            {formatPaymentMethodLabel(order.payment_method)} •{" "}
            {order.payment_status}
          </span>
          {order.payment_reference && (
            <span className="badge bg-light text-dark border px-3 py-2 font-monospace">
              Ref: {order.payment_reference}
            </span>
          )}
        </div>
      </div>

      <div className="sg-two-col-layout" style={{ marginBottom: 0 }}>
        <section className="sg-panel">
          <h2 className="fs-5 fw-bold mb-3">Purchased Items</h2>
          {order.items?.map((item, idx) => (
            <div
              key={`${item.product_id}-${idx}`}
              className="d-flex align-items-center justify-content-between gap-3 py-3 border-bottom"
            >
              <div className="d-flex align-items-center gap-3">
                <img
                  src={item.image_url}
                  alt={item.product_name}
                  onError={handleProductImageError}
                  style={{
                    width: "72px",
                    height: "50px",
                    objectFit: "cover",
                    borderRadius: "8px",
                  }}
                />
                <div>
                  <div className="fw-bold">{item.product_name}</div>
                  <div className="text-muted small">
                    Qty {item.quantity} × {formatINR(item.unit_price)}
                  </div>
                </div>
              </div>
              <strong>{formatINR(item.line_total)}</strong>
            </div>
          ))}

          <div className="mt-3 pt-2 d-grid gap-1 small">
            <div className="d-flex justify-content-between">
              <span className="text-muted">Subtotal</span>
              <span>{formatINR(order.subtotal_amount)}</span>
            </div>
            <div className="d-flex justify-content-between">
              <span className="text-muted">Shipping</span>
              <span>
                {order.shipping_amount === 0
                  ? "FREE"
                  : formatINR(order.shipping_amount)}
              </span>
            </div>
            <div className="d-flex justify-content-between">
              <span className="text-muted">Included GST</span>
              <span>{formatINR(order.tax_amount)}</span>
            </div>
            <div className="d-flex justify-content-between fw-bold fs-5 pt-2 border-top mt-2">
              <span>Order Total</span>
              <span>{formatINR(order.total_amount)}</span>
            </div>
          </div>
        </section>

        <aside className="sg-panel">
          <h2 className="fs-5 fw-bold mb-3">Delivery &amp; Billing Summary</h2>
          <div className="mb-3">
            <div className="small text-muted fw-semibold text-uppercase">
              Shipping Address
            </div>
            <div className="fw-semibold mt-1">{order.shipping_full_name}</div>
            {order.shipping_phone && (
              <div className="small text-muted">{order.shipping_phone}</div>
            )}
            {order.shipping_email && (
              <div className="small text-muted">{order.shipping_email}</div>
            )}
            <p className="small mt-1 mb-0">{order.shipping_address || "—"}</p>
          </div>

          <div className="mb-4 pt-3 border-top">
            <div className="small text-muted fw-semibold text-uppercase">
              Billing Address
            </div>
            <p className="small mt-1 mb-0">
              {order.billing_address || order.shipping_address || "—"}
            </p>
          </div>

          <div className="d-grid gap-2">
            {isAuthenticated && (
              <Link to="/my-orders" className="sg-btn-primary w-100">
                <i className="bi bi-box-seam"></i>
                View My Orders
              </Link>
            )}
            <Link to="/" className="btn btn-outline-secondary w-100">
              Continue Shopping
            </Link>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default OrderConfirmationPage;
