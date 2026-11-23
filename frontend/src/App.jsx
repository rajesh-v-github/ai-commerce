import { useEffect, useState } from "react";

import LoginPage from "./pages/LoginPage";
import CopilotPage from "./pages/CopilotPage";
import "./App.css";

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(
    () =>
      !!localStorage.getItem("token") &&
      localStorage.getItem("role") === "support",
  );
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    if (localStorage.getItem("role") !== "support") {
      localStorage.removeItem("token");
      localStorage.removeItem("role");
    }

    const handleSessionExpired = () => setSessionExpired(true);

    window.addEventListener("auth:session-expired", handleSessionExpired);
    return () =>
      window.removeEventListener("auth:session-expired", handleSessionExpired);
  }, []);

  const handleLogin = () => {
    setSessionExpired(false);
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    setSessionExpired(false);
    setIsLoggedIn(false);
  };

  const returnToLogin = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    setIsLoggedIn(false);
  };

  return (
    <>
      {isLoggedIn ? (
        <>
          <CopilotPage onLogout={handleLogout} />
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
                  For your security, please sign in again to continue using
                  your support workspace.
                </p>
                <button
                  className="btn btn-primary session-expired-action"
                  onClick={returnToLogin}
                  type="button"
                >
                  Return to sign in
                  <i className="bi bi-arrow-right" aria-hidden="true"></i>
                </button>
              </section>
            </div>
          )}
        </>
      ) : (
        <LoginPage onLogin={handleLogin} sessionExpired={sessionExpired} />
      )}
    </>
  );
}

export default App;
