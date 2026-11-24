import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/authContextObject";
import { useToast } from "../context/toastContextObject";

function StoreAuthPage({ initialMode = "login" }) {
  const [mode, setMode] = useState(initialMode);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loginUser, registerUser } = useAuth();
  const { showToast } = useToast();

  const redirectTo = searchParams.get("redirect") || "";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      setSubmitting(true);
      if (mode === "login") {
        const result = await loginUser(username.trim(), password);
        showToast(
          `Welcome back, ${result.profile?.full_name || result.profile?.username}!`,
          "success",
        );
        if (redirectTo) {
          navigate(redirectTo, { replace: true });
        } else if (result.role === "support") {
          navigate("/admin", { replace: true });
        } else {
          navigate("/", { replace: true });
        }
      } else {
        const result = await registerUser({
          username: username.trim(),
          full_name: fullName.trim(),
          email: email.trim(),
          phone: phone.trim() || undefined,
          password,
        });
        showToast(
          `Account created! Welcome to SoranoGear, ${result.profile?.full_name}.`,
          "success",
        );
        navigate(redirectTo || "/", { replace: true });
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : mode === "login"
            ? "Invalid username/email or password."
            : "Unable to create customer account. Please verify all fields.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="sg-container py-5">
      <div className="sg-panel mx-auto" style={{ maxWidth: "460px" }}>
        <div className="text-center mb-4">
          <span className="sg-brand-mark mx-auto mb-2" aria-hidden="true">
            <i className="bi bi-cpu"></i>
          </span>
          <h1 className="fs-4 fw-bold">
            {mode === "login"
              ? "Sign in to SoranoGear"
              : "Create Customer Account"}
          </h1>
          <p className="text-muted small mt-1">
            {mode === "login"
              ? "Customers and Support Executives can sign in here."
              : "Track orders, save addresses, and check out faster."}
          </p>
        </div>

        <div className="btn-group w-100 mb-4" role="group">
          <button
            type="button"
            className={`btn btn-sm ${
              mode === "login" ? "btn-primary" : "btn-outline-secondary"
            }`}
            onClick={() => {
              setMode("login");
              setError("");
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`btn btn-sm ${
              mode === "register" ? "btn-primary" : "btn-outline-secondary"
            }`}
            onClick={() => {
              setMode("register");
              setError("");
            }}
          >
            Create Customer Account
          </button>
        </div>

        {error && (
          <div className="alert alert-danger py-2 small" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="d-grid gap-3">
          {mode === "register" && (
            <>
              <div>
                <label className="form-label small fw-semibold" htmlFor="auth-fullname">
                  Full Name *
                </label>
                <input
                  id="auth-fullname"
                  type="text"
                  className="form-control"
                  required
                  minLength={2}
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Priya Nair"
                />
              </div>
              <div>
                <label className="form-label small fw-semibold" htmlFor="auth-email">
                  Email Address *
                </label>
                <input
                  id="auth-email"
                  type="email"
                  className="form-control"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="priya@example.com"
                />
              </div>
              <div>
                <label className="form-label small fw-semibold" htmlFor="auth-phone">
                  Phone Number (Optional)
                </label>
                <input
                  id="auth-phone"
                  type="tel"
                  className="form-control"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+91 98765 00000"
                />
              </div>
            </>
          )}

          <div>
            <label className="form-label small fw-semibold" htmlFor="auth-username">
              {mode === "login" ? "Username or Email *" : "Username *"}
            </label>
            <input
              id="auth-username"
              type="text"
              className="form-control"
              required
              minLength={3}
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={mode === "login" ? "customer1 or support1" : "priya_nair"}
            />
          </div>

          <div>
            <label className="form-label small fw-semibold" htmlFor="auth-password">
              Password *
            </label>
            <input
              id="auth-password"
              type="password"
              className="form-control"
              required
              minLength={mode === "register" ? 8 : 1}
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={
                mode === "register" ? "Minimum 8 characters" : "••••••••"
              }
            />
          </div>

          <button
            type="submit"
            className="sg-btn-primary w-100 mt-1"
            disabled={submitting}
          >
            {submitting
              ? "Signing in..."
              : mode === "login"
                ? "Sign In"
                : "Create Account"}
          </button>
        </form>

        <div className="text-center mt-3 pt-3 border-top small text-muted">
          <Link to="/" className="text-decoration-none">
            ← Return to SoranoGear Storefront
          </Link>
        </div>
      </div>
    </div>
  );
}

export default StoreAuthPage;
