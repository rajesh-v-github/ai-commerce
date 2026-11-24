import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import { AuthProvider } from "./context/AuthProvider";
import { useAuth } from "./context/authContextObject";
import { CartProvider } from "./context/CartProvider";
import { ToastProvider } from "./context/ToastProvider";

import StorefrontLayout from "./storefront/StorefrontLayout";
import StoreHomePage from "./storefront/StoreHomePage";
import ProductDetailPage from "./storefront/ProductDetailPage";
import CartPage from "./storefront/CartPage";
import CheckoutPage from "./storefront/CheckoutPage";
import OrderConfirmationPage from "./storefront/OrderConfirmationPage";
import CustomerOrdersPage from "./storefront/CustomerOrdersPage";
import StoreAuthPage from "./storefront/StoreAuthPage";

import RequireExecutive from "./admin/RequireExecutive";
import AdminLayout from "./admin/AdminLayout";
import AdminOverviewSection from "./admin/AdminOverviewSection";
import AdminProductsSection from "./admin/AdminProductsSection";
import AdminOrdersSection from "./admin/AdminOrdersSection";
import AdminCustomersSection from "./admin/AdminCustomersSection";

import LoginPage from "./pages/LoginPage";
import CopilotPage from "./pages/CopilotPage";
import "./App.css";

function SupportWorkspaceRoute() {
  const {
    isAuthenticated,
    isSupportExecutive,
    loading,
    sessionExpired,
    clearSessionExpired,
    syncLegacyLogin,
    logoutUser,
  } = useAuth();
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="d-flex align-items-center justify-content-center vh-100">
        <div className="spinner-border text-primary" role="status"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <LoginPage
        sessionExpired={sessionExpired}
        onLogin={async () => {
          await syncLegacyLogin();
        }}
      />
    );
  }

  if (!isSupportExecutive) {
    return <RequireExecutive>{null}</RequireExecutive>;
  }

  return (
    <>
      <CopilotPage
        onLogout={() => {
          logoutUser();
          navigate("/support");
        }}
      />
      {sessionExpired && (
        <div className="session-expired-backdrop">
          <section
            className="session-expired-dialog"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="session-expired-title"
            aria-describedby="session-expired-message"
          >
            <span className="session-expired-icon" aria-hidden="true">
              <i className="bi bi-clock-history"></i>
            </span>
            <h2 id="session-expired-title">Your session has ended</h2>
            <p id="session-expired-message">
              For your security, please sign in again to continue using your
              support workspace.
            </p>
            <button
              className="btn btn-primary session-expired-action"
              onClick={() => {
                logoutUser();
                clearSessionExpired();
              }}
              type="button"
            >
              Return to sign in
              <i className="bi bi-arrow-right" aria-hidden="true"></i>
            </button>
          </section>
        </div>
      )}
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <CartProvider>
            <Routes>
              {/* Customer-Facing E-Commerce Storefront (Accessible to Customers & Support Executives) */}
              <Route element={<StorefrontLayout />}>
                <Route path="/" element={<StoreHomePage />} />
                <Route
                  path="/product/:productId"
                  element={<ProductDetailPage />}
                />
                <Route path="/cart" element={<CartPage />} />
                <Route path="/checkout" element={<CheckoutPage />} />
                <Route
                  path="/order-confirmation/:orderNumber"
                  element={<OrderConfirmationPage />}
                />
                <Route path="/my-orders" element={<CustomerOrdersPage />} />
                <Route
                  path="/login"
                  element={<StoreAuthPage key="login" initialMode="login" />}
                />
                <Route
                  path="/register"
                  element={
                    <StoreAuthPage key="register" initialMode="register" />
                  }
                />
              </Route>

              {/* Existing AI-Powered Customer Support Executive Workspace */}
              <Route path="/support" element={<SupportWorkspaceRoute />} />

              {/* Executive-Only Admin Dashboard at /admin */}
              <Route
                path="/admin"
                element={
                  <RequireExecutive>
                    <AdminLayout />
                  </RequireExecutive>
                }
              >
                <Route index element={<AdminOverviewSection />} />
                <Route path="products" element={<AdminProductsSection />} />
                <Route path="orders" element={<AdminOrdersSection />} />
                <Route path="customers" element={<AdminCustomersSection />} />
              </Route>

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </CartProvider>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}

export default App;
