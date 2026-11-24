import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/authContextObject";
import { useCart } from "../context/cartContextObject";
import { useToast } from "../context/toastContextObject";
import { submitStoreCheckout } from "../services/storeService";
import { formatINR, handleProductImageError } from "../utils/formatters";

const PAYMENT_OPTIONS = [
  {
    id: "MOCK_CARD",
    title: "Simulated Credit / Debit Card (POC)",
    subtitle: "Instant simulated card authorization — no real card numbers collected.",
    icon: "bi-credit-card-2-front",
  },
  {
    id: "MOCK_UPI",
    title: "Simulated UPI Instant Pay (POC)",
    subtitle: "Instant simulated UPI authorization for demonstration workflows.",
    icon: "bi-phone-flip",
  },
  {
    id: "MOCK_COD",
    title: "Pay on Delivery (POC)",
    subtitle: "Order recorded with PENDING payment status until delivery.",
    icon: "bi-cash-stack",
  },
];

function makeIdempotencyKey() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return `sg-chk-${crypto.randomUUID()}`;
  }
  return `sg-chk-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function CheckoutPage() {
  const { isAuthenticated, user } = useAuth();
  const {
    lines,
    itemCount,
    subtotal,
    shipping,
    includedGst,
    total,
    warnings,
    clearCart,
    refreshValidation,
  } = useCart();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const idempotencyRef = useRef(makeIdempotencyKey());

  const [fullName, setFullName] = useState(
    () => user?.full_name || user?.username || "",
  );
  const [email, setEmail] = useState(() => user?.email || "");
  const [phone, setPhone] = useState(() => user?.phone || "");
  const [shipLine1, setShipLine1] = useState(
    () => user?.shipping_address || "",
  );
  const [shipLine2, setShipLine2] = useState("");
  const [shipCity, setShipCity] = useState("");
  const [shipState, setShipState] = useState("");
  const [shipPostal, setShipPostal] = useState("");
  const [shipCountry, setShipCountry] = useState("India");

  const [sameAsShipping, setSameAsShipping] = useState(true);
  const [billLine1, setBillLine1] = useState("");
  const [billLine2, setBillLine2] = useState("");
  const [billCity, setBillCity] = useState("");
  const [billState, setBillState] = useState("");
  const [billPostal, setBillPostal] = useState("");
  const [billCountry, setBillCountry] = useState("India");

  const [paymentMethod, setPaymentMethod] = useState("MOCK_CARD");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const [hydratedUserId, setHydratedUserId] = useState(() => user?.id ?? null);
  if (user && user.id !== hydratedUserId) {
    setHydratedUserId(user.id);
    if (!fullName) {
      setFullName(user.full_name || user.username || "");
    }
    if (!email) {
      setEmail(user.email || "");
    }
    if (!phone) {
      setPhone(user.phone || "");
    }
    if (!shipLine1 && user.shipping_address) {
      setShipLine1(user.shipping_address);
    }
  }

  if (lines.length === 0) {
    return (
      <div className="sg-container py-5">
        <div className="sg-panel text-center py-5">
          <i
            className="bi bi-bag text-muted"
            style={{ fontSize: "42px" }}
          ></i>
          <h1 className="fs-4 fw-bold mt-3">Your cart is empty</h1>
          <p className="text-muted mt-1 mb-3">
            Add products to your cart before proceeding to checkout.
          </p>
          <Link to="/" className="sg-btn-primary">
            Return to Storefront
          </Link>
        </div>
      </div>
    );
  }

  const handleSubmitOrder = async (event) => {
    event.preventDefault();
    setFormError("");

    if (!fullName.trim() || !email.trim() || !phone.trim()) {
      setFormError("Please complete all customer contact fields.");
      return;
    }
    if (!shipLine1.trim() || !shipCity.trim() || !shipState.trim() || !shipPostal.trim()) {
      setFormError("Please complete your shipping address details.");
      return;
    }
    if (
      !sameAsShipping &&
      (!billLine1.trim() || !billCity.trim() || !billState.trim() || !billPostal.trim())
    ) {
      setFormError("Please complete your billing address details.");
      return;
    }

    try {
      setSubmitting(true);
      const payload = {
        items: lines
          .filter((l) => l.quantity > 0)
          .map((l) => ({
            product_id: l.product_id,
            quantity: l.quantity,
          })),
        customer_full_name: fullName.trim(),
        customer_email: email.trim(),
        customer_phone: phone.trim(),
        shipping_address: {
          line1: shipLine1.trim(),
          line2: shipLine2.trim(),
          city: shipCity.trim(),
          state: shipState.trim(),
          postal_code: shipPostal.trim(),
          country: shipCountry.trim() || "India",
        },
        same_as_shipping: sameAsShipping,
        billing_address: sameAsShipping
          ? null
          : {
              line1: billLine1.trim(),
              line2: billLine2.trim(),
              city: billCity.trim(),
              state: billState.trim(),
              postal_code: billPostal.trim(),
              country: billCountry.trim() || "India",
            },
        payment_method: paymentMethod,
        notes: notes.trim() || null,
        idempotency_key: idempotencyRef.current,
      };

      const orderReceipt = await submitStoreCheckout(payload);
      await clearCart();
      showToast(
        `Order ${orderReceipt.order_number} placed successfully!`,
        "success",
      );
      const refParam = orderReceipt.payment_reference
        ? `?ref=${encodeURIComponent(orderReceipt.payment_reference)}`
        : "";
      navigate(
        `/order-confirmation/${encodeURIComponent(orderReceipt.order_number)}${refParam}`,
        { state: { order: orderReceipt } },
      );
    } catch (error) {
      console.error(error);
      // Generate a fresh idempotency key if validation/stock failed so user can retry after fixing
      idempotencyRef.current = makeIdempotencyKey();
      await refreshValidation();
      const detail = error.response?.data?.detail;
      setFormError(
        typeof detail === "string"
          ? detail
          : "Unable to place your order. Please verify stock availability and your details.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="sg-container py-4">
      <div className="mb-3">
        <Link to="/cart" className="text-decoration-none small fw-semibold">
          <i className="bi bi-arrow-left me-1"></i>
          Back to Cart
        </Link>
        <h1 className="fs-2 fw-bold mt-1">Secure Checkout</h1>
      </div>

      {!isAuthenticated && (
        <div className="alert alert-light border d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
          <span className="small">
            <i className="bi bi-person-check me-2 text-primary"></i>
            Already have a SoranoGear account? Sign in to track orders in one
            place.
          </span>
          <Link
            to="/login?redirect=/checkout"
            className="btn btn-sm btn-outline-primary"
          >
            Sign In
          </Link>
        </div>
      )}

      {formError && (
        <div className="alert alert-danger" role="alert">
          <i className="bi bi-exclamation-octagon-fill me-2"></i>
          {formError}
        </div>
      )}

      {warnings.map((w, idx) => (
        <div key={idx} className="alert alert-warning">
          {w}
        </div>
      ))}

      <form onSubmit={handleSubmitOrder} className="sg-two-col-layout">
        <div className="d-grid gap-4">
          {/* 1. Customer Information */}
          <section className="sg-panel">
            <h2 className="fs-5 fw-bold mb-3">
              1. Customer Contact Information
            </h2>
            <div className="row g-3">
              <div className="col-md-6">
                <label className="form-label small fw-semibold" htmlFor="chk-name">
                  Full Name *
                </label>
                <input
                  id="chk-name"
                  type="text"
                  className="form-control"
                  required
                  placeholder="Aarav Sharma"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
              <div className="col-md-6">
                <label className="form-label small fw-semibold" htmlFor="chk-phone">
                  Phone Number *
                </label>
                <input
                  id="chk-phone"
                  type="tel"
                  className="form-control"
                  required
                  placeholder="+91 98765 43210"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
              <div className="col-12">
                <label className="form-label small fw-semibold" htmlFor="chk-email">
                  Email Address (for order confirmation &amp; customer lookup) *
                </label>
                <input
                  id="chk-email"
                  type="email"
                  className="form-control"
                  required
                  placeholder="aarav@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>
          </section>

          {/* 2. Shipping & Billing */}
          <section className="sg-panel">
            <h2 className="fs-5 fw-bold mb-3">2. Shipping &amp; Billing Address</h2>
            <div className="row g-3">
              <div className="col-12">
                <label className="form-label small fw-semibold" htmlFor="ship-line1">
                  Street Address / Building *
                </label>
                <input
                  id="ship-line1"
                  type="text"
                  className="form-control"
                  required
                  placeholder="Plot 42, HITEC City Main Road"
                  value={shipLine1}
                  onChange={(e) => setShipLine1(e.target.value)}
                />
              </div>
              <div className="col-12">
                <label className="form-label small fw-semibold" htmlFor="ship-line2">
                  Apartment, Suite, Landmark (Optional)
                </label>
                <input
                  id="ship-line2"
                  type="text"
                  className="form-control"
                  placeholder="Floor 4, Wing B"
                  value={shipLine2}
                  onChange={(e) => setShipLine2(e.target.value)}
                />
              </div>
              <div className="col-md-4">
                <label className="form-label small fw-semibold" htmlFor="ship-city">
                  City *
                </label>
                <input
                  id="ship-city"
                  type="text"
                  className="form-control"
                  required
                  placeholder="Hyderabad"
                  value={shipCity}
                  onChange={(e) => setShipCity(e.target.value)}
                />
              </div>
              <div className="col-md-4">
                <label className="form-label small fw-semibold" htmlFor="ship-state">
                  State *
                </label>
                <input
                  id="ship-state"
                  type="text"
                  className="form-control"
                  required
                  placeholder="Telangana"
                  value={shipState}
                  onChange={(e) => setShipState(e.target.value)}
                />
              </div>
              <div className="col-md-4">
                <label className="form-label small fw-semibold" htmlFor="ship-pin">
                  PIN / Postal Code *
                </label>
                <input
                  id="ship-pin"
                  type="text"
                  className="form-control"
                  required
                  placeholder="500081"
                  value={shipPostal}
                  onChange={(e) => setShipPostal(e.target.value)}
                />
              </div>
              <div className="col-md-6">
                <label className="form-label small fw-semibold" htmlFor="ship-country">
                  Country *
                </label>
                <input
                  id="ship-country"
                  type="text"
                  className="form-control"
                  required
                  value={shipCountry}
                  onChange={(e) => setShipCountry(e.target.value)}
                />
              </div>
            </div>

            <div className="form-check mt-3">
              <input
                id="same-billing"
                type="checkbox"
                className="form-check-input"
                checked={sameAsShipping}
                onChange={(e) => setSameAsShipping(e.target.checked)}
              />
              <label className="form-check-label small fw-semibold" htmlFor="same-billing">
                Billing address is the same as shipping address
              </label>
            </div>

            {!sameAsShipping && (
              <div className="row g-3 mt-2 pt-3 border-top">
                <h3 className="fs-6 fw-bold mb-1">Billing Address</h3>
                <div className="col-12">
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Billing Street Address *"
                    required={!sameAsShipping}
                    value={billLine1}
                    onChange={(e) => setBillLine1(e.target.value)}
                  />
                </div>
                <div className="col-12">
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Billing Suite / Landmark (Optional)"
                    value={billLine2}
                    onChange={(e) => setBillLine2(e.target.value)}
                  />
                </div>
                <div className="col-md-4">
                  <input
                    type="text"
                    className="form-control"
                    placeholder="City *"
                    required={!sameAsShipping}
                    value={billCity}
                    onChange={(e) => setBillCity(e.target.value)}
                  />
                </div>
                <div className="col-md-4">
                  <input
                    type="text"
                    className="form-control"
                    placeholder="State *"
                    required={!sameAsShipping}
                    value={billState}
                    onChange={(e) => setBillState(e.target.value)}
                  />
                </div>
                <div className="col-md-4">
                  <input
                    type="text"
                    className="form-control"
                    placeholder="PIN Code *"
                    required={!sameAsShipping}
                    value={billPostal}
                    onChange={(e) => setBillPostal(e.target.value)}
                  />
                </div>
                <div className="col-md-6">
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Country *"
                    required={!sameAsShipping}
                    value={billCountry}
                    onChange={(e) => setBillCountry(e.target.value)}
                  />
                </div>
              </div>
            )}
          </section>

          {/* 3. POC Mock Payment Method */}
          <section className="sg-panel">
            <h2 className="fs-5 fw-bold mb-2">
              3. Payment Method (POC Simulation)
            </h2>
            <div className="sg-poc-banner mb-3">
              <i className="bi bi-info-circle-fill mt-1"></i>
              <div>
                <strong>Safe POC Payment Mode:</strong> This checkout simulates
                payment confirmation for demonstration and order-lifecycle
                testing. No real financial transaction is executed and no card
                credentials are collected.
              </div>
            </div>

            <div className="d-grid gap-2">
              {PAYMENT_OPTIONS.map((opt) => (
                <label
                  key={opt.id}
                  className={`sg-payment-option ${
                    paymentMethod === opt.id ? "selected" : ""
                  }`}
                >
                  <input
                    type="radio"
                    name="payment_method"
                    value={opt.id}
                    checked={paymentMethod === opt.id}
                    onChange={() => setPaymentMethod(opt.id)}
                    className="form-check-input mt-1"
                  />
                  <div>
                    <div className="fw-bold d-flex align-items-center gap-2">
                      <i className={`bi ${opt.icon} text-primary`}></i>
                      {opt.title}
                    </div>
                    <div className="text-muted small">{opt.subtitle}</div>
                  </div>
                </label>
              ))}
            </div>

            <div className="mt-3">
              <label className="form-label small fw-semibold" htmlFor="chk-notes">
                Delivery Instructions / Notes (Optional)
              </label>
              <textarea
                id="chk-notes"
                rows="2"
                className="form-control"
                placeholder="Leave at reception desk or call before arrival..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </section>
        </div>

        {/* Order Review & Place Order Sidebar */}
        <aside className="sg-panel" style={{ position: "sticky", top: "96px" }}>
          <h2 className="fs-5 fw-bold mb-3">Order Review ({itemCount})</h2>

          <div className="d-grid gap-2 mb-3" style={{ maxHeight: "280px", overflowY: "auto" }}>
            {lines.map((line) => (
              <div
                key={line.product_id}
                className="d-flex align-items-center justify-content-between gap-2 py-2 border-bottom"
              >
                <div className="d-flex align-items-center gap-2" style={{ minWidth: 0 }}>
                  <img
                    src={line.product?.image_url}
                    alt={line.product?.name}
                    onError={handleProductImageError}
                    style={{
                      width: "52px",
                      height: "38px",
                      objectFit: "cover",
                      borderRadius: "6px",
                    }}
                  />
                  <div className="text-truncate">
                    <div className="fw-semibold small text-truncate">
                      {line.product?.name}
                    </div>
                    <div className="text-muted" style={{ fontSize: "12px" }}>
                      Qty: {line.quantity} × {formatINR(line.unit_price)}
                    </div>
                  </div>
                </div>
                <strong className="small">{formatINR(line.line_total)}</strong>
              </div>
            ))}
          </div>

          <div className="d-grid gap-2 small mb-3">
            <div className="d-flex justify-content-between">
              <span className="text-muted">Subtotal</span>
              <span className="fw-semibold">{formatINR(subtotal)}</span>
            </div>
            <div className="d-flex justify-content-between">
              <span className="text-muted">Shipping</span>
              <span className="fw-semibold">
                {shipping === 0 ? "FREE" : formatINR(shipping)}
              </span>
            </div>
            <div className="d-flex justify-content-between">
              <span className="text-muted">Included GST (18%)</span>
              <span>{formatINR(includedGst)}</span>
            </div>
          </div>

          <hr />

          <div className="d-flex justify-content-between align-items-center mb-3">
            <span className="fw-bold fs-5">Total Payable</span>
            <span className="fs-4" style={{ fontWeight: 800 }}>
              {formatINR(total)}
            </span>
          </div>

          <button
            type="submit"
            className="sg-btn-primary w-100"
            disabled={submitting || lines.some((l) => l.quantity <= 0)}
          >
            {submitting ? (
              <>
                <span className="spinner-border spinner-border-sm"></span>
                Placing Order...
              </>
            ) : (
              <>
                <i className="bi bi-check2-circle"></i>
                Place Order ({formatINR(total)})
              </>
            )}
          </button>

          <p className="text-muted text-center mt-2 mb-0" style={{ fontSize: "11.5px" }}>
            Inventory is verified atomically upon submission.
          </p>
        </aside>
      </form>
    </div>
  );
}

export default CheckoutPage;
