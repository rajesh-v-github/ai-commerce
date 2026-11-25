import { Link, useNavigate } from "react-router-dom";
import { useCart } from "../context/cartContextObject";
import { formatINR, handleProductImageError } from "../utils/formatters";

function CartPage() {
  const {
    lines,
    itemCount,
    subtotal,
    shipping,
    includedGst,
    total,
    amountToFreeShipping,
    warnings,
    updateQuantity,
    removeItem,
    clearCart,
  } = useCart();
  const navigate = useNavigate();

  return (
    <div className="sg-container py-4">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <div>
          <h1 className="fs-2 fw-bold">Shopping Cart</h1>
          <p className="text-muted small mb-0">
            {itemCount} {itemCount === 1 ? "item" : "items"} in your bag
          </p>
        </div>
        {lines.length > 0 && (
          <button
            type="button"
            className="btn btn-sm btn-outline-danger"
            onClick={clearCart}
          >
            <i className="bi bi-trash3 me-1"></i>
            Clear Cart
          </button>
        )}
      </div>

      {warnings.map((w, idx) => (
        <div key={idx} className="alert alert-warning">
          <i className="bi bi-exclamation-triangle-fill me-2"></i>
          {w}
        </div>
      ))}

      {lines.length === 0 ? (
        <div className="sg-panel text-center py-5 mb-5">
          <i
            className="bi bi-cart-x text-muted"
            style={{ fontSize: "46px" }}
          ></i>
          <h2 className="fs-4 fw-bold mt-3">Your shopping cart is empty</h2>
          <p className="text-muted mt-1 mb-4">
            Add laptops, audio gear, or workspace accessories to get started.
          </p>
          <Link to="/" className="sg-btn-primary">
            Explore SoranoGear
          </Link>
        </div>
      ) : (
        <div className="sg-two-col-layout">
          <div className="sg-panel">
            {lines.map((line) => (
              <div
                key={line.product_id}
                className="d-flex flex-wrap align-items-center justify-content-between gap-3 py-3 border-bottom"
              >
                <div className="d-flex align-items-center gap-3" style={{ minWidth: "240px", flex: 1 }}>
                  <Link to={`/product/${line.product_id}`}>
                    <img
                      src={line.product?.image_url}
                      alt={line.product?.name}
                      onError={handleProductImageError}
                      style={{
                        width: "96px",
                        height: "66px",
                        objectFit: "cover",
                        borderRadius: "10px",
                      }}
                    />
                  </Link>
                  <div>
                    <span className="text-uppercase small fw-bold text-primary d-block">
                      {line.product?.category}
                    </span>
                    <Link
                      to={`/product/${line.product_id}`}
                      className="fw-bold text-dark text-decoration-none fs-6"
                    >
                      {line.product?.name}
                    </Link>
                    <div className="text-muted small">
                      Unit Price: {formatINR(line.unit_price)} •{" "}
                      {line.available_stock} in stock
                    </div>
                  </div>
                </div>

                <div className="d-flex align-items-center gap-3">
                  <div className="sg-qty-stepper">
                    <button
                      type="button"
                      onClick={() =>
                        updateQuantity(line.product_id, line.quantity - 1)
                      }
                    >
                      −
                    </button>
                    <span>{line.quantity}</span>
                    <button
                      type="button"
                      disabled={line.quantity >= line.available_stock}
                      onClick={() =>
                        updateQuantity(line.product_id, line.quantity + 1)
                      }
                    >
                      +
                    </button>
                  </div>

                  <strong style={{ minWidth: "95px", textAlign: "right" }}>
                    {formatINR(line.line_total)}
                  </strong>

                  <button
                    type="button"
                    className="btn btn-sm btn-outline-danger"
                    onClick={() => removeItem(line.product_id)}
                    aria-label={`Remove ${line.product?.name}`}
                  >
                    <i className="bi bi-trash3"></i>
                  </button>
                </div>
              </div>
            ))}
          </div>

          <aside className="sg-panel">
            <h2 className="fs-5 fw-bold mb-3">Order Summary</h2>

            {amountToFreeShipping > 0 ? (
              <div className="alert alert-info py-2 small">
                Add <strong>{formatINR(amountToFreeShipping)}</strong> more to
                unlock <strong>FREE Express Delivery</strong>!
              </div>
            ) : (
              <div className="alert alert-success py-2 small">
                <i className="bi bi-truck me-1"></i>
                Your order qualifies for <strong>FREE Express Delivery</strong>.
              </div>
            )}

            <div className="d-grid gap-2 small mb-3">
              <div className="d-flex justify-content-between">
                <span className="text-muted">Subtotal ({itemCount} items)</span>
                <span className="fw-semibold">{formatINR(subtotal)}</span>
              </div>
              <div className="d-flex justify-content-between">
                <span className="text-muted">Express Delivery</span>
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

            <div className="d-flex justify-content-between align-items-center mb-4">
              <span className="fw-bold fs-5">Order Total</span>
              <span className="fw-extrabold fs-4" style={{ fontWeight: 800 }}>
                {formatINR(total)}
              </span>
            </div>

            <button
              type="button"
              className="sg-btn-primary w-100 mb-2"
              disabled={lines.some((l) => l.quantity <= 0)}
              onClick={() => navigate("/checkout")}
            >
              Proceed to Checkout
              <i className="bi bi-lock-fill"></i>
            </button>

            <Link
              to="/"
              className="btn btn-outline-secondary w-100 btn-sm mt-1"
            >
              Continue Shopping
            </Link>
          </aside>
        </div>
      )}
    </div>
  );
}

export default CartPage;
