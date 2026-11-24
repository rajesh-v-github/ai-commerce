import { useCallback, useMemo, useState } from "react";
import { ToastContext } from "./toastContextObject";

let nextToastId = 1;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const showToast = useCallback(
    (message, variant = "info", durationMs = 4200) => {
      const id = nextToastId++;
      setToasts((prev) => [...prev.slice(-4), { id, message, variant }]);
      if (durationMs > 0) {
        window.setTimeout(() => {
          dismissToast(id);
        }, durationMs);
      }
      return id;
    },
    [dismissToast],
  );

  const value = useMemo(
    () => ({ showToast, dismissToast }),
    [showToast, dismissToast],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="sg-toast-stack" aria-live="polite" aria-atomic="true">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`sg-toast sg-toast-${toast.variant}`}
            role="status"
          >
            <i
              className={`bi ${
                toast.variant === "success"
                  ? "bi-check-circle-fill"
                  : toast.variant === "danger"
                    ? "bi-exclamation-octagon-fill"
                    : toast.variant === "warning"
                      ? "bi-exclamation-triangle-fill"
                      : "bi-info-circle-fill"
              }`}
              aria-hidden="true"
            ></i>
            <span>{toast.message}</span>
            <button
              type="button"
              className="sg-toast-close"
              onClick={() => dismissToast(toast.id)}
              aria-label="Dismiss notification"
            >
              <i className="bi bi-x-lg" aria-hidden="true"></i>
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
