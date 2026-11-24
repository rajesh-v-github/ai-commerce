import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/authContextObject";
import { useToast } from "../context/toastContextObject";
import { fetchAdminAiStatus, fetchAdminOrders } from "../services/adminService";
import { formatINR } from "../utils/formatters";
import "./Admin.css";

function AdminLayout() {
  const { user, token, sessionExpired, logoutUser } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [aiStatus, setAiStatus] = useState(null);
  const [pendingOrderCount, setPendingOrderCount] = useState(0);
  const [newIncomingCount, setNewIncomingCount] = useState(0);
  const [lastSyncedAt, setLastSyncedAt] = useState(null);
  const latestOrderIdRef = useRef(null);

  useEffect(() => {
    let active = true;
    fetchAdminAiStatus()
      .then((data) => {
        if (active) {
          setAiStatus(data);
        }
      })
      .catch(() => {
        if (active) {
          setAiStatus({ available: false, model: "llama3.2:1b" });
        }
      });
    return () => {
      active = false;
    };
  }, []);

  // Near-real-time incoming order monitor (10-second polling)
  useEffect(() => {
    if (!token || sessionExpired) {
      return;
    }
    let active = true;

    const pollIncomingOrders = async () => {
      try {
        const data = await fetchAdminOrders();
        if (!active || !data?.orders) {
          return;
        }
        setLastSyncedAt(new Date());
        const pendingCount = data.orders.filter(
          (o) => o.status === "PROCESSING" || o.status === "CONFIRMED",
        ).length;
        setPendingOrderCount(pendingCount);

        if (data.orders.length > 0) {
          const newest = data.orders[0];
          if (
            latestOrderIdRef.current !== null &&
            newest.id > latestOrderIdRef.current
          ) {
            const newlyArrived = data.orders.filter(
              (o) => o.id > latestOrderIdRef.current,
            );
            setNewIncomingCount((prev) => prev + newlyArrived.length);
            showToast(
              `New order ${newest.order_number} (${formatINR(newest.total_amount)}) received from ${newest.shipping_full_name || newest.customer_name}!`,
              "info",
            );
          }
          latestOrderIdRef.current = Math.max(
            latestOrderIdRef.current || 0,
            newest.id,
          );
        }
      } catch {
        // Ignore transient background poll errors
      }
    };

    pollIncomingOrders();
    const timer = setInterval(pollIncomingOrders, 10000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [token, sessionExpired, showToast]);

  const handleLogout = () => {
    logoutUser();
    navigate("/login");
  };

  return (
    <div className="sorano-admin">
      <aside className="adm-sidebar">
        <Link to="/admin" className="adm-brand">
          <span className="adm-brand-icon">
            <i className="bi bi-speedometer2"></i>
          </span>
          <div>
            <div className="fw-bold lh-sm">SoranoGear Admin</div>
            <div style={{ fontSize: "11px", color: "#94a3b8" }}>
              Executive Command Center
            </div>
          </div>
        </Link>

        <div className="adm-nav-label">Commerce Operations</div>
        <NavLink
          to="/admin"
          end
          className={({ isActive }) =>
            `adm-nav-link ${isActive ? "active" : ""}`
          }
        >
          <span>
            <i className="bi bi-grid-1x2-fill me-2"></i>
            Overview &amp; KPIs
          </span>
        </NavLink>

        <NavLink
          to="/admin/products"
          className={({ isActive }) =>
            `adm-nav-link ${isActive ? "active" : ""}`
          }
        >
          <span>
            <i className="bi bi-box-seam-fill me-2"></i>
            Products &amp; Inventory
          </span>
        </NavLink>

        <NavLink
          to="/admin/orders"
          onClick={() => setNewIncomingCount(0)}
          className={({ isActive }) =>
            `adm-nav-link ${isActive ? "active" : ""}`
          }
        >
          <span>
            <i className="bi bi-receipt-cutoff me-2"></i>
            Orders
          </span>
          {(newIncomingCount > 0 || pendingOrderCount > 0) && (
            <span
              className={`badge rounded-pill ${
                newIncomingCount > 0 ? "text-bg-success" : "text-bg-secondary"
              }`}
              title={
                newIncomingCount > 0
                  ? `${newIncomingCount} newly placed order(s) since last view`
                  : `${pendingOrderCount} unshipped order(s) awaiting fulfillment (Processing or Confirmed)`
              }
              aria-label={
                newIncomingCount > 0
                  ? `${newIncomingCount} newly placed orders`
                  : `${pendingOrderCount} orders awaiting fulfillment`
              }
            >
              {newIncomingCount > 0 ? `+${newIncomingCount} new` : pendingOrderCount}
            </span>
          )}
        </NavLink>

        <NavLink
          to="/admin/customers"
          className={({ isActive }) =>
            `adm-nav-link ${isActive ? "active" : ""}`
          }
        >
          <span>
            <i className="bi bi-people-fill me-2"></i>
            Customers
          </span>
        </NavLink>

        <div className="adm-nav-label mt-3">Connected Workspaces</div>
        <Link to="/support" className="adm-nav-link">
          <span>
            <i className="bi bi-robot me-2"></i>
            Support AI Copilot
          </span>
          <i className="bi bi-arrow-up-right small"></i>
        </Link>

        <Link to="/" className="adm-nav-link">
          <span>
            <i className="bi bi-shop me-2"></i>
            Live Storefront
          </span>
          <i className="bi bi-arrow-up-right small"></i>
        </Link>

        <div className="mt-auto pt-3 border-top border-secondary border-opacity-25 d-none d-lg-block">
          <div className="d-flex align-items-center justify-content-between small mb-2">
            <span className="text-secondary">AI Engine</span>
            <span
              className={`badge ${
                aiStatus?.ready || aiStatus?.available
                  ? "bg-success-subtle text-success"
                  : "bg-warning-subtle text-warning"
              }`}
              title={
                aiStatus?.ollama_available && aiStatus?.model_ready
                  ? `Connected to local Ollama (${aiStatus?.configured_model})`
                  : "Built-in Grounded AI Copywriter active (connect local Ollama anytime for LLM inference)"
              }
            >
              {aiStatus?.ollama_available && aiStatus?.model_ready
                ? `Ollama • ${aiStatus?.configured_model || "llama3.2:1b"}`
                : aiStatus?.ready
                  ? "Built-in AI Ready"
                  : "AI Standby"}
            </span>
          </div>
          <div className="small text-secondary text-truncate mb-2">
            Signed in as <strong className="text-white">{user?.username}</strong>
          </div>
          <button
            type="button"
            className="btn btn-sm btn-outline-light w-100"
            onClick={handleLogout}
          >
            <i className="bi bi-box-arrow-right me-1"></i>
            Sign Out
          </button>
        </div>
      </aside>

      <div className="adm-main">
        <header className="adm-topbar">
          <div className="d-flex align-items-center gap-3">
            <span className="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1">
              <i className="bi bi-shield-check me-1"></i>
              Support Executive Access
            </span>
            {lastSyncedAt && (
              <span className="text-muted small d-none d-md-inline">
                <i className="bi bi-broadcast text-success me-1"></i>
                Live order feed synced{" "}
                {lastSyncedAt.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </span>
            )}
          </div>

          <div className="d-flex align-items-center gap-2">
            <Link to="/support" className="btn btn-sm btn-outline-primary">
              <i className="bi bi-headset me-1"></i>
              Support Workspace
            </Link>
            <Link to="/" className="btn btn-sm btn-outline-secondary">
              <i className="bi bi-bag me-1"></i>
              View Store
            </Link>
          </div>
        </header>

        <main className="adm-content">
          <Outlet context={{ aiStatus, lastSyncedAt }} />
        </main>
      </div>
    </div>
  );
}

export default AdminLayout;
