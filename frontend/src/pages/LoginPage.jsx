import { useState } from "react";
import { login } from "../services/authService";
import { persistAuthTokenAndRole } from "../services/authStorage";
import soranoLogo from "../assets/sorano-logo.png";
import "./LoginPage.css";

function LoginPage({ onLogin, sessionExpired = false }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [accessDenied, setAccessDenied] = useState(false);

  // Persist the authenticated session before switching back to the workspace.
  const handleLogin = async (event) => {
    event.preventDefault();
    setAccessDenied(false);

    try {
      const response = await login(username, password);

      if (response.role !== "support") {
        setAccessDenied(true);
        return;
      }

      persistAuthTokenAndRole(response.access_token, response.role);

      onLogin();
    } catch (error) {
      console.error(error);

      alert("Invalid username or password");
    }
  };

  return (
    <div className="login-workspace">
      <img className="login-company-logo" src={soranoLogo} alt="SoranoTech" />
      <main className="login-main">
        <section className="login-card">
          <div className="login-brand">
            <span className="login-logo" aria-hidden="true">
              <i className="bi bi-headset"></i>
            </span>
            <div className="login-brand-copy">
              <p className="login-eyebrow">CUSTOMER EXPERIENCE OPERATIONS</p>
              <p>Executive workspace sign in</p>
            </div>
          </div>

          <div className="login-divider"></div>

          {/* Explain why credentials are requested again after an expired session. */}
          {sessionExpired && (
            <div className="alert alert-info session-expired-notice" role="status">
              Your session expired. Sign in again to return to your support
              workspace.
            </div>
          )}

          {accessDenied && (
            <div className="alert alert-warning login-access-denied" role="alert">
              <strong>Support executive access required</strong>
              <p>
                This portal is only available to authorized support executives.
                Customer accounts cannot access the support workspace. Please
                sign in with a support executive account, or contact the support
                team if you need help with your order.
              </p>
            </div>
          )}

          {/* <div className="login-welcome">
            <h2>Welcome back</h2>
            <p>Sign in to continue to your support workspace.</p>
          </div> */}

          <form onSubmit={handleLogin}>
            <div className="login-field">
              <label className="form-label" htmlFor="support-username">
                Username
              </label>
              <div className="login-input-wrap">
                <i className="bi bi-person" aria-hidden="true"></i>
                <input
                  id="support-username"
                  type="text"
                  className="form-control"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>
            </div>

            <div className="login-field">
              <label className="form-label" htmlFor="support-password">
                Password
              </label>
              <div className="login-input-wrap">
                <i className="bi bi-lock" aria-hidden="true"></i>
                <input
                  id="support-password"
                  type="password"
                  className="form-control"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <button
              className="btn btn-primary login-submit"
              type="submit"
            >
              Sign in
              <i className="bi bi-arrow-right" aria-hidden="true"></i>
            </button>
          </form>
        </section>
      </main>

    </div>
  );
}

export default LoginPage;
