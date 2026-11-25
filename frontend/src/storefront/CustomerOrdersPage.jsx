import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/authContextObject";
import { useToast } from "../context/toastContextObject";
import { updateCurrentProfile } from "../services/authService";
import { getMyOrders } from "../services/storeService";
import {
  formatDateTime,
  formatINR,
  formatPaymentMethodLabel,
  handleProductImageError,
} from "../utils/formatters";

function CustomerOrdersPage() {
  const { isAuthenticated, user, refreshProfile } = useAuth();
  const { showToast } = useToast();

  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedOrderId, setExpandedOrderId] = useState(null);

  const [editingProfile, setEditingProfile] = useState(false);
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [shippingAddress, setShippingAddress] = useState(
    user?.shipping_address || "",
  );
  const [savingProfile, setSavingProfile] = useState(false);

  const openEditProfile = () => {
    if (!editingProfile) {
      setFullName(user?.full_name || "");
      setEmail(user?.email || "");
      setPhone(user?.phone || "");
      setShippingAddress(user?.shipping_address || "");
    }
    setEditingProfile((v) => !v);
  };

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    let active = true;
    getMyOrders()
      .then((data) => {
        if (active) {
          setOrders(data || []);
        }
      })
      .catch((err) => console.error(err))
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <Navigate to="/login?redirect=/my-orders" replace />;
  }

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    try {
      setSavingProfile(true);
      await updateCurrentProfile({
        full_name: fullName,
        email: email || undefined,
        phone,
        shipping_address: shippingAddress,
      });
      await refreshProfile();
      setEditingProfile(false);
      showToast("Account profile updated.", "success");
    } catch (err) {
      const detail = err.response?.data?.detail;
      showToast(
        typeof detail === "string" ? detail : "Unable to update profile.",
        "danger",
      );
    } finally {
      setSavingProfile(false);
    }
  };

  const statusBadge = (status) => {
    switch ((status || "").toUpperCase()) {
      case "DELIVERED":
        return "badge text-bg-success";
      case "SHIPPED":
        return "badge text-bg-info";
      case "CONFIRMED":
        return "badge text-bg-primary";
      case "CANCELLED":
        return "badge text-bg-danger";
      default:
        return "badge text-bg-warning";
    }
  };

  return (
    <div className="sg-container py-4 mb-5">
      <div className="sg-two-col-layout">
        <section>
          <div className="d-flex justify-content-between align-items-center mb-3">
            <div>
              <h1 className="fs-2 fw-bold">My Orders</h1>
              <p className="text-muted small mb-0">
                Track purchases placed under your account
              </p>
            </div>
            <Link to="/" className="btn btn-sm btn-outline-primary">
              + New Order
            </Link>
          </div>

          {loading ? (
            <div className="sg-panel text-center py-5">
              <div className="spinner-border text-primary" role="status"></div>
              <p className="text-muted mt-2">Loading your order history...</p>
            </div>
          ) : orders.length === 0 ? (
            <div className="sg-panel text-center py-5">
              <i
                className="bi bi-box-seam text-muted"
                style={{ fontSize: "40px" }}
              ></i>
              <h2 className="fs-5 fw-bold mt-3">No orders placed yet</h2>
              <p className="text-muted small mt-1 mb-3">
                Once you place an order on SoranoGear, its status and items will
                appear here.
              </p>
              <Link to="/" className="sg-btn-primary">
                Browse Products
              </Link>
            </div>
          ) : (
            <div className="d-grid gap-3">
              {orders.map((order) => {
                const isExpanded = expandedOrderId === order.id;
                return (
                  <article key={order.id} className="sg-panel">
                    <div className="d-flex flex-wrap justify-content-between align-items-center gap-2">
                      <div>
                        <span className="font-monospace fw-bold fs-6 me-2">
                          {order.order_number}
                        </span>
                        <span className={statusBadge(order.status)}>
                          {order.status}
                        </span>
                        <div className="text-muted small mt-1">
                          Placed {formatDateTime(order.created_at)} •{" "}
                          {order.item_count}{" "}
                          {order.item_count === 1 ? "item" : "items"} •{" "}
                          {formatPaymentMethodLabel(order.payment_method)} (
                          {order.payment_status})
                        </div>
                      </div>

                      <div className="d-flex align-items-center gap-3">
                        <strong className="fs-5">
                          {formatINR(order.total_amount)}
                        </strong>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() =>
                            setExpandedOrderId(isExpanded ? null : order.id)
                          }
                        >
                          {isExpanded ? "Hide Details" : "View Details"}
                        </button>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="mt-3 pt-3 border-top">
                        <div className="d-grid gap-2 mb-3">
                          {(order.items || []).map((item, idx) => (
                            <div
                              key={`${item.product_id}-${idx}`}
                              className="d-flex align-items-center justify-content-between gap-2"
                            >
                              <div className="d-flex align-items-center gap-2">
                                <img
                                  src={item.image_url}
                                  alt={item.product_name}
                                  onError={handleProductImageError}
                                  style={{
                                    width: "56px",
                                    height: "40px",
                                    objectFit: "cover",
                                    borderRadius: "6px",
                                  }}
                                />
                                <div>
                                  <div className="fw-semibold small">
                                    {item.product_name}
                                  </div>
                                  <div className="text-muted small">
                                    {item.quantity} × {formatINR(item.unit_price)}
                                  </div>
                                </div>
                              </div>
                              <strong className="small">
                                {formatINR(item.line_total)}
                              </strong>
                            </div>
                          ))}
                        </div>

                        {order.shipping_address && (
                          <p className="small text-muted mb-2">
                            <strong>Ship to:</strong> {order.shipping_address}
                          </p>
                        )}

                        {order.status_history?.length > 0 && (
                          <div className="bg-light rounded p-3 small">
                            <strong className="d-block mb-2">
                              Order Timeline
                            </strong>
                            {order.status_history.map((h) => (
                              <div
                                key={h.id}
                                className="d-flex justify-content-between text-muted py-1"
                              >
                                <span>
                                  {h.old_status
                                    ? `${h.old_status} → ${h.new_status}`
                                    : h.new_status}
                                  {h.note ? ` — ${h.note}` : ""}
                                </span>
                                <span>{formatDateTime(h.changed_at)}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <aside className="sg-panel">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h2 className="fs-5 fw-bold mb-0">Account Profile</h2>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={openEditProfile}
            >
              {editingProfile ? "Cancel" : "Edit"}
            </button>
          </div>

          {!editingProfile ? (
            <div className="d-grid gap-2 small">
              <div>
                <span className="text-muted d-block">Username</span>
                <strong className="font-monospace">{user?.username}</strong>
              </div>
              <div>
                <span className="text-muted d-block">Full Name</span>
                <strong>{user?.full_name || "—"}</strong>
              </div>
              <div>
                <span className="text-muted d-block">Email</span>
                <strong>{user?.email || "—"}</strong>
              </div>
              <div>
                <span className="text-muted d-block">Phone</span>
                <strong>{user?.phone || "—"}</strong>
              </div>
              <div>
                <span className="text-muted d-block">Saved Shipping Address</span>
                <span>{user?.shipping_address || "—"}</span>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSaveProfile} className="d-grid gap-3">
              <div>
                <label className="form-label small fw-semibold">Full Name</label>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
              <div>
                <label className="form-label small fw-semibold">Email</label>
                <input
                  type="email"
                  className="form-control form-control-sm"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div>
                <label className="form-label small fw-semibold">Phone</label>
                <input
                  type="tel"
                  className="form-control form-control-sm"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
              <div>
                <label className="form-label small fw-semibold">
                  Default Shipping Address
                </label>
                <textarea
                  rows="2"
                  className="form-control form-control-sm"
                  value={shippingAddress}
                  onChange={(e) => setShippingAddress(e.target.value)}
                />
              </div>
              <button
                type="submit"
                className="btn btn-primary btn-sm"
                disabled={savingProfile}
              >
                {savingProfile ? "Saving..." : "Save Profile"}
              </button>
            </form>
          )}
        </aside>
      </div>
    </div>
  );
}

export default CustomerOrdersPage;
