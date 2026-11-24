import { useEffect, useState } from "react";
import {
  Link,
  Outlet,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import soranoLogo from "../assets/sorano-logo.png";
import { useAuth } from "../context/authContextObject";
import { useCart } from "../context/cartContextObject";
import { useToast } from "../context/toastContextObject";
import { formatINR, handleProductImageError } from "../utils/formatters";
import "./Storefront.css";

const NAV_CATEGORIES = [
  { label: "All Gear", value: "" },
  { label: "Laptops", value: "Laptops" },
  { label: "Audio", value: "Audio" },
  { label: "Gaming", value: "Gaming Accessories" },
  { label: "Keyboards & Mice", value: "Keyboards & Mice" },
  { label: "Monitors", value: "Monitors & Displays" },
  { label: "Accessories", value: "Computer Accessories" },
  { label: "Webcams", value: "Webcams" },
  { label: "Wearables", value: "Wearables" },
  { label: "Laptop Bags", value: "Laptop Bags" },
  { label: "Power & Charging", value: "Power & Charging" },
];

function StorefrontLayout({ children }) {
  const { isAuthenticated, isExecutive, user, logoutUser } = useAuth();
  const {
    lines,
    itemCount,
    subtotal,
    shipping,
    total,
    amountToFreeShipping,
    warnings,
    drawerOpen,
    setDrawerOpen,
    updateQuantity,
    removeItem,
  } = useCart();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [headerQuery, setHeaderQuery] = useState(
    () => searchParams.get("q") || "",
  );

  const activeCategory =
    location.pathname === "/" ? searchParams.get("category") || "" : null;

  const urlSearchQuery = searchParams.get("q") || "";
  const [prevUrlSearch, setPrevUrlSearch] = useState(urlSearchQuery);
  if (urlSearchQuery !== prevUrlSearch) {
    setPrevUrlSearch(urlSearchQuery);
    setHeaderQuery(urlSearchQuery);
  }

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [location.pathname, location.search]);

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    const trimmed = headerQuery.trim();
    navigate(trimmed ? `/?q=${encodeURIComponent(trimmed)}` : "/");
  };

  const handleLogout = () => {
    logoutUser();
    showToast("Signed out successfully.", "info");
    navigate("/");
  };

  return (
    <div className="sorano-storefront">
      {isExecutive && (
        <div className="sg-exec-ribbon">
          <div className="sg-container sg-exec-ribbon-inner">
            <div>
              <span className="sg-exec-badge">
                <i className="bi bi-shield-lock-fill" aria-hidden="true"></i>
                EXECUTIVE SESSION
              </span>{" "}
              <span className="ms-2">
                Signed in as <strong>{user?.username || "Executive"}</strong>
              </span>
            </div>
            <div className="sg-exec-links">
              <Link to="/admin" className="sg-exec-link">
                <i className="bi bi-speedometer2" aria-hidden="true"></i>
                Admin Dashboard (/admin)
              </Link>
              <Link to="/support" className="sg-exec-link">
                <i className="bi bi-headset" aria-hidden="true"></i>
                CS AI Workspace
              </Link>
            </div>
          </div>
        </div>
      )}

      <div className="sg-promo-bar">
        <div className="sg-container">
          <i className="bi bi-truck me-2" aria-hidden="true"></i>
          Free Express Delivery across India on orders of ₹1,999+ • Official SoranoTech Hardware Storefront
        </div>
      </div>

      <header className="sg-header">
        <div className="sg-container">
          <div className="sg-header-main">
            <Link to="/" className="sg-brand">
              <span className="sg-brand-mark" aria-hidden="true">
                <i className="bi bi-cpu"></i>
              </span>
              <span className="sg-brand-text">
                <strong>SoranoGear</strong>
                <small>by SoranoTech</small>
              </span>
            </Link>

            <form className="sg-header-search" onSubmit={handleSearchSubmit}>
              <i
                className="bi bi-search sg-search-icon"
                aria-hidden="true"
              ></i>
              <input
                type="search"
                placeholder="Search laptops, earbuds, mechanical keyboards, monitors..."
                aria-label="Search products"
                value={headerQuery}
                onChange={(e) => setHeaderQuery(e.target.value)}
              />
            </form>

            <div className="sg-header-actions">
              {isAuthenticated ? (
                <>
                  <Link to="/my-orders" className="sg-nav-btn">
                    <i className="bi bi-box-seam" aria-hidden="true"></i>
                    <span className="d-none d-md-inline">
                      {user?.username || "Account"}
                    </span>
                  </Link>
                  <button
                    type="button"
                    className="sg-nav-btn"
                    onClick={handleLogout}
                    title="Sign out"
                  >
                    <i className="bi bi-box-arrow-right" aria-hidden="true"></i>
                    <span className="d-none d-lg-inline">Sign out</span>
                  </button>
                </>
              ) : (
                <Link to="/login" className="sg-nav-btn">
                  <i className="bi bi-person" aria-hidden="true"></i>
                  <span>Sign In</span>
                </Link>
              )}

              <button
                type="button"
                className="sg-nav-btn sg-cart-trigger"
                onClick={() => setDrawerOpen(true)}
                aria-label={`Shopping cart with ${itemCount} items`}
              >
                <i className="bi bi-bag" aria-hidden="true"></i>
                <span className="d-none d-sm-inline">Cart</span>
                <span className="sg-cart-badge">{itemCount}</span>
              </button>
            </div>
          </div>

          <nav className="sg-category-strip" aria-label="Product categories">
            {NAV_CATEGORIES.map((cat) => {
              const targetUrl = cat.value
                ? `/?category=${encodeURIComponent(cat.value)}`
                : "/";
              return (
                <Link
                  key={cat.label}
                  to={targetUrl}
                  className={`sg-cat-pill text-decoration-none ${
                    activeCategory === cat.value ? "active" : ""
                  }`}
                >
                  {cat.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      <main style={{ flex: 1 }}>{children || <Outlet />}</main>

      {/* Slide-over Mini Cart Drawer */}
      {drawerOpen && (
        <div
          className="sg-drawer-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setDrawerOpen(false);
            }
          }}
        >
          <aside
            className="sg-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Shopping Cart"
          >
            <div className="sg-drawer-header">
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: 800 }}>
                  Your Cart ({itemCount})
                </h3>
                {amountToFreeShipping > 0 && lines.length > 0 ? (
                  <small className="text-muted">
                    Add {formatINR(amountToFreeShipping)} more for Free Express
                    Delivery
                  </small>
                ) : lines.length > 0 ? (
                  <small className="text-success fw-semibold">
                    <i className="bi bi-check-circle-fill me-1"></i>
                    Unlocked Free Express Delivery!
                  </small>
                ) : null}
              </div>
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                onClick={() => setDrawerOpen(false)}
                aria-label="Close cart drawer"
              >
                <i className="bi bi-x-lg"></i>
              </button>
            </div>

            <div className="sg-drawer-body">
              {warnings.map((w, idx) => (
                <div key={idx} className="alert alert-warning py-2 small">
                  {w}
                </div>
              ))}

              {lines.length === 0 ? (
                <div className="text-center py-5">
                  <i
                    className="bi bi-bag-x text-muted"
                    style={{ fontSize: "40px" }}
                  ></i>
                  <p className="mt-3 fw-semibold">Your cart is empty</p>
                  <p className="text-muted small mb-3">
                    Explore laptops, wireless audio, gaming gear, and desk
                    essentials.
                  </p>
                  <button
                    type="button"
                    className="sg-btn-primary"
                    onClick={() => {
                      setDrawerOpen(false);
                      navigate("/");
                    }}
                  >
                    Browse Catalog
                  </button>
                </div>
              ) : (
                lines.map((line) => (
                  <div key={line.product_id} className="sg-cart-line">
                    <img
                      src={line.product?.image_url}
                      alt={line.product?.name}
                      onError={handleProductImageError}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <Link
                        to={`/product/${line.product_id}`}
                        onClick={() => setDrawerOpen(false)}
                        className="fw-bold text-decoration-none text-dark d-block text-truncate"
                      >
                        {line.product?.name}
                      </Link>
                      <div className="text-muted small mb-2">
                        {formatINR(line.unit_price)} each
                      </div>
                      <div className="d-flex align-items-center justify-content-between">
                        <div className="sg-qty-stepper">
                          <button
                            type="button"
                            onClick={() =>
                              updateQuantity(line.product_id, line.quantity - 1)
                            }
                            aria-label="Decrease quantity"
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
                            aria-label="Increase quantity"
                          >
                            +
                          </button>
                        </div>
                        <div className="d-flex align-items-center gap-2">
                          <strong>{formatINR(line.line_total)}</strong>
                          <button
                            type="button"
                            className="btn btn-sm text-danger p-1"
                            onClick={() => removeItem(line.product_id)}
                            aria-label={`Remove ${line.product?.name}`}
                          >
                            <i className="bi bi-trash3"></i>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {lines.length > 0 && (
              <div className="sg-drawer-footer">
                <div className="d-flex justify-content-between small text-muted mb-1">
                  <span>Subtotal</span>
                  <span>{formatINR(subtotal)}</span>
                </div>
                <div className="d-flex justify-content-between small text-muted mb-2">
                  <span>Shipping</span>
                  <span>{shipping === 0 ? "FREE" : formatINR(shipping)}</span>
                </div>
                <div className="d-flex justify-content-between fw-bold fs-5 mb-3">
                  <span>Total</span>
                  <span>{formatINR(total)}</span>
                </div>
                <div className="d-grid gap-2">
                  <button
                    type="button"
                    className="sg-btn-primary w-100"
                    onClick={() => {
                      setDrawerOpen(false);
                      navigate("/checkout");
                    }}
                  >
                    Proceed to Checkout
                    <i className="bi bi-arrow-right"></i>
                  </button>
                  <Link
                    to="/cart"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setDrawerOpen(false)}
                  >
                    View Full Cart
                  </Link>
                </div>
              </div>
            )}
          </aside>
        </div>
      )}

      <footer className="sg-footer">
        <div className="sg-container">
          <div className="sg-footer-grid">
            <div>
              <div className="d-flex align-items-center gap-2 mb-3">
                <span className="sg-brand-mark" aria-hidden="true">
                  <i className="bi bi-cpu"></i>
                </span>
                <div>
                  <strong className="text-white fs-5 d-block">SoranoGear</strong>
                  <small className="text-secondary">
                    A SoranoTech Commerce Experience
                  </small>
                </div>
              </div>
              <p className="small text-secondary mb-3">
                Curated laptops, studio-grade personal audio, mechanical gaming
                gear, and workspace peripherals backed by AI-powered SoranoTech
                customer support.
              </p>
              <img
                src={soranoLogo}
                alt="SoranoTech"
                style={{
                  height: "34px",
                  filter: "invert(1) brightness(1.8)",
                  opacity: 0.85,
                }}
              />
            </div>

            <div>
              <h4>Categories</h4>
              <ul>
                <li>
                  <Link to="/?category=Laptops">Laptops &amp; Notebooks</Link>
                </li>
                <li>
                  <Link to="/?category=Audio">Wireless Audio</Link>
                </li>
                <li>
                  <Link to="/?category=Gaming+Accessories">Gaming Gear</Link>
                </li>
                <li>
                  <Link to="/?category=Monitors+%26+Displays">
                    Monitors &amp; Displays
                  </Link>
                </li>
                <li>
                  <Link to="/?category=Keyboards+%26+Mice">
                    Keyboards &amp; Mice
                  </Link>
                </li>
              </ul>
            </div>

            <div>
              <h4>Customer Care</h4>
              <ul>
                <li>
                  <Link to="/cart">Shopping Cart</Link>
                </li>
                <li>
                  <Link to="/my-orders">Track My Orders</Link>
                </li>
                <li>
                  <Link to="/login">Customer Sign In</Link>
                </li>
                <li>
                  <Link to="/register">Create Account</Link>
                </li>
              </ul>
            </div>

            <div>
              <h4>POC Environment Notice</h4>
              <p className="small text-secondary mb-2">
                Checkout uses a safe simulated POC payment workflow. No real
                financial cards or bank transfers are processed.
              </p>
              {isExecutive && (
                <div className="d-flex flex-wrap gap-2 mt-2">
                  <Link to="/admin" className="btn btn-sm btn-outline-light">
                    Admin Console
                  </Link>
                  <Link to="/support" className="btn btn-sm btn-outline-info">
                    Support Copilot
                  </Link>
                </div>
              )}
            </div>
          </div>

          <div className="d-flex flex-wrap justify-content-between align-items-center pt-3 small text-secondary">
            <span>
              © {new Date().getFullYear()} SoranoGear • Powered by SoranoTech.
            </span>
            <span>INR (₹) Pricing • Real-Time Inventory Sync</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default StorefrontLayout;
