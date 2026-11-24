import { Link, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/authContextObject";
import "./Admin.css";

function RequireExecutive({ children }) {
  const { isAuthenticated, isSupportExecutive, loading, user, logoutUser } =
    useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="d-flex flex-column align-items-center justify-content-center vh-100 bg-light">
        <div className="spinner-border text-primary" role="status"></div>
        <p className="text-muted small mt-2">
          Verifying executive credentials...
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    const redirectTarget = encodeURIComponent(
      `${location.pathname}${location.search}`,
    );
    return <Navigate to={`/login?redirect=${redirectTarget}`} replace />;
  }

  if (!isSupportExecutive) {
    return (
      <div
        className="sorano-admin d-flex align-items-center justify-content-center p-4"
        style={{ display: "flex" }}
      >
        <div
          className="adm-card text-center p-5"
          style={{ maxWidth: "520px" }}
        >
          <div
            className="d-inline-grid rounded-circle bg-danger-subtle text-danger mb-3"
            style={{ width: "64px", height: "64px", placeItems: "center", fontSize: "28px" }}
          >
            <i className="bi bi-shield-lock-fill"></i>
          </div>
          <span className="badge text-bg-danger mb-2">HTTP 403 • Forbidden</span>
          <h1 className="fs-4 fw-bold">Executive Authorization Required</h1>
          <p className="text-muted small mt-2 mb-4">
            You are signed in as{" "}
            <strong>{user?.username || "a customer"}</strong> (role:{" "}
            <code>{user?.role || "customer"}</code>). The{" "}
            <code>/admin</code> Commerce Command Center is strictly restricted
            to authenticated Customer Support Executives.
          </p>
          <div className="d-flex flex-wrap justify-content-center gap-2">
            <Link to="/" className="btn btn-primary">
              <i className="bi bi-shop me-1"></i>
              Return to Storefront
            </Link>
            <Link to="/my-orders" className="btn btn-outline-secondary">
              My Orders
            </Link>
            <button
              type="button"
              className="btn btn-outline-danger"
              onClick={logoutUser}
            >
              Sign Out &amp; Switch Account
            </button>
          </div>
        </div>
      </div>
    );
  }

  return children;
}

export default RequireExecutive;
