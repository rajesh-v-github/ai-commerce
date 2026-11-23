import "./DashboardTab.css";

const ORDER_STATUS_COLORS = {
  PROCESSING: "dashboard-status-processing",
  SHIPPED: "dashboard-status-shipped",
  DELIVERED: "dashboard-status-delivered",
  CANCELLED: "dashboard-status-cancelled",
};

function formatActivityDate(value) {
  if (!value) {
    return "No activity recorded";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function DashboardTab({
  overview,
  loading,
  error,
  onRetry,
  onFilterTickets,
  onViewTicket,
  onViewOrder,
  onViewOrders,
}) {
  if (loading && !overview) {
    return (
      <div className="dashboard-state" role="status">
        <span className="spinner-border" aria-hidden="true"></span>
        <p>Loading your support overview…</p>
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div className="dashboard-state dashboard-state-error" role="alert">
        <i className="bi bi-exclamation-circle" aria-hidden="true"></i>
        <p>{error}</p>
        <button className="btn btn-primary" onClick={onRetry} type="button">
          Try again
        </button>
      </div>
    );
  }

  if (!overview) {
    return null;
  }

  const ticketCounts = overview.ticket_status_counts || {};
  const orderCounts = overview.order_status_counts || {};
  const totalOrdersByStatus = Object.values(orderCounts).reduce(
    (total, count) => total + count,
    0,
  );
  const trend = overview.ticket_activity_trend;
  const peakActivity = Math.max(
    1,
    ...(trend?.daily || []).map((day) => day.count),
  );

  const ticketMetrics = [
    {
      label: "Open tickets",
      status: "OPEN",
      value: ticketCounts.OPEN || 0,
      icon: "bi-inbox",
      tone: "open",
      hint: "Needs initial review",
    },
    {
      label: "In-progress tickets",
      status: "IN_PROGRESS",
      value: ticketCounts.IN_PROGRESS || 0,
      icon: "bi-arrow-repeat",
      tone: "progress",
      hint: "Being worked on",
    },
    {
      label: "Resolved tickets",
      status: "RESOLVED",
      value: ticketCounts.RESOLVED || 0,
      icon: "bi-check2-circle",
      tone: "resolved",
      hint: "Completed",
    },
    {
      label: "All tickets",
      status: null,
      value: overview.total_tickets || 0,
      icon: "bi-ticket-detailed",
      tone: "tickets",
      hint: "View every ticket",
    },
  ];

  return (
    <section className="dashboard-tab" aria-labelledby="dashboard-title">
      <header className="dashboard-heading">
        <div>
          <p className="workspace-eyebrow">SUPPORT OPERATIONS</p>
          <h2 id="dashboard-title">Dashboard</h2>
          <p>Workload, recent activity, and order health in one place.</p>
        </div>
        <button
          className="btn btn-outline-secondary dashboard-refresh"
          onClick={onRetry}
          disabled={loading}
          type="button"
        >
          <i
            className={`bi ${loading ? "bi-arrow-repeat" : "bi-arrow-clockwise"}`}
            aria-hidden="true"
          ></i>
          Refresh
        </button>
      </header>

      {error && (
        <div className="alert alert-warning dashboard-inline-error" role="alert">
          {error}
        </div>
      )}

      <div className="dashboard-metrics">
        {ticketMetrics.map((metric) => (
          <button
            className={`dashboard-metric dashboard-metric-${metric.tone}`}
            key={metric.label}
            onClick={() => onFilterTickets(metric.status)}
            type="button"
          >
            <span className="dashboard-metric-icon" aria-hidden="true">
              <i className={`bi ${metric.icon}`}></i>
            </span>
            <span className="dashboard-metric-value">{metric.value}</span>
            <span className="dashboard-metric-label">{metric.label}</span>
            <span className="dashboard-metric-hint">{metric.hint}</span>
            <i
              className="bi bi-arrow-up-right dashboard-metric-arrow"
              aria-hidden="true"
            ></i>
          </button>
        ))}
        <button
          className="dashboard-metric dashboard-metric-orders"
          onClick={onViewOrders}
          type="button"
        >
          <span className="dashboard-metric-icon" aria-hidden="true">
            <i className="bi bi-bag-check"></i>
          </span>
          <span className="dashboard-metric-value">{overview.total_orders}</span>
          <span className="dashboard-metric-label">Total orders</span>
          <span className="dashboard-metric-hint">Review the order list</span>
          <i
            className="bi bi-arrow-up-right dashboard-metric-arrow"
            aria-hidden="true"
          ></i>
        </button>
      </div>

      <div className="dashboard-content-grid">
        <div className="dashboard-column">
          <section className="card dashboard-card dashboard-attention">
            <div className="card-header dashboard-section-heading">
              <span>
                <i className="bi bi-lightning-charge" aria-hidden="true"></i>
                Needs attention
              </span>
              <small>
                {(overview.attention_tickets || []).length} active tickets
              </small>
            </div>
            <div className="dashboard-list">
              {overview.attention_tickets?.length ? (
                overview.attention_tickets.map((ticket) => (
                  <article className="dashboard-attention-row" key={ticket.id}>
                    <div className="dashboard-attention-main">
                      <button
                        className="dashboard-ticket-link"
                        onClick={() => onViewTicket(ticket.ticket_number)}
                        type="button"
                      >
                        {ticket.ticket_number}
                      </button>
                      <span
                        className={`dashboard-status-pill dashboard-status-${ticket.status.toLowerCase()}`}
                      >
                        {ticket.status.replace("_", " ")}
                      </span>
                      <span className="dashboard-priority">
                        {ticket.priority}
                      </span>
                      <p>{ticket.subject}</p>
                      <small>
                        {ticket.days_since_activity === null
                          ? "No activity timestamp available"
                          : ticket.days_since_activity === 0
                            ? `Last activity ${formatActivityDate(ticket.last_activity_at)}`
                            : `Last activity ${ticket.days_since_activity} day${ticket.days_since_activity === 1 ? "" : "s"} ago`}
                      </small>
                    </div>
                    <button
                      className="btn btn-sm btn-outline-secondary dashboard-view-button"
                      onClick={() => onViewTicket(ticket.ticket_number)}
                      type="button"
                    >
                      Review
                    </button>
                  </article>
                ))
              ) : (
                <div className="dashboard-empty">
                  <i className="bi bi-check2-circle" aria-hidden="true"></i>
                  <p>No open or in-progress tickets need attention.</p>
                </div>
              )}
            </div>
          </section>

          <section className="card dashboard-card dashboard-trend-card">
            <div className="card-header dashboard-section-heading">
              <span>
                <i className="bi bi-activity" aria-hidden="true"></i>
                Support activity
              </span>
              <small>Last 7 days</small>
            </div>
            <div className="dashboard-trend-summary">
              <strong>{trend?.current_period_count || 0}</strong>
              <span>messages and status changes</span>
            </div>
            <div
              className="dashboard-trend-chart"
              role="img"
              aria-label="Daily support messages and status changes for the last seven days"
            >
              {(trend?.daily || []).map((day) => {
                const date = new Date(`${day.date}T00:00:00`);
                return (
                  <div className="dashboard-trend-day" key={day.date}>
                    <span className="dashboard-trend-count">{day.count}</span>
                    <div className="dashboard-trend-track">
                      <span
                        style={{
                          height: `${Math.max((day.count / peakActivity) * 100, day.count ? 8 : 0)}%`,
                        }}
                      ></span>
                    </div>
                    <span className="dashboard-trend-label">
                      {new Intl.DateTimeFormat(undefined, {
                        weekday: "short",
                      }).format(date)}
                    </span>
                  </div>
                );
              })}
            </div>
            <p className="dashboard-trend-comparison">
              {trend?.change_percent === null ||
              trend?.change_percent === undefined
                ? "No activity in the previous 7-day period to compare."
                : `${trend.change_percent > 0 ? "+" : ""}${trend.change_percent}% compared with the previous 7 days.`}
            </p>
          </section>

          <section className="card dashboard-card dashboard-orders-card">
            <div className="card-header dashboard-section-heading">
              <span>
                <i className="bi bi-receipt" aria-hidden="true"></i>
                Latest order records
              </span>
              <button
                className="dashboard-inline-link"
                onClick={onViewOrders}
                type="button"
              >
                View all
              </button>
            </div>
            <div className="dashboard-list">
              {overview.recent_orders?.length ? (
                overview.recent_orders.map((order) => (
                  <article className="dashboard-order-row" key={order.id}>
                    <div>
                      <button
                        className="dashboard-ticket-link dashboard-order-number"
                        onClick={() => onViewOrder(order.order_number)}
                        type="button"
                        aria-label={`View details for order ${order.order_number}`}
                      >
                        {order.order_number}
                      </button>
                      <span>{order.customer_name}</span>
                    </div>
                    <div className="dashboard-order-meta">
                      <span
                        className={`dashboard-status-pill dashboard-status-${order.status.toLowerCase()}`}
                      >
                        {order.status}
                      </span>
                      <strong>
                        {new Intl.NumberFormat(undefined, {
                          style: "currency",
                          currency: "INR",
                          maximumFractionDigits: 2,
                        }).format(order.total_amount)}
                      </strong>
                    </div>
                  </article>
                ))
              ) : (
                <div className="dashboard-empty">
                  <p>No order records are available.</p>
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="dashboard-column">
          <section className="card dashboard-card">
            <div className="card-header dashboard-section-heading">
              <span>
                <i className="bi bi-box-seam" aria-hidden="true"></i>
                Order health
              </span>
              <small>{overview.total_orders} orders</small>
            </div>
            <div className="dashboard-order-statuses">
              {Object.entries(orderCounts).map(([status, count]) => {
                const share = totalOrdersByStatus
                  ? (count / totalOrdersByStatus) * 100
                  : 0;
                return (
                  <div className="dashboard-order-status" key={status}>
                    <div className="dashboard-order-status-label">
                      <span>{status.replace("_", " ")}</span>
                      <strong>{count}</strong>
                    </div>
                    <div
                      className="dashboard-progress-track"
                      role="progressbar"
                      aria-label={`${status} orders`}
                      aria-valuemin="0"
                      aria-valuemax={totalOrdersByStatus}
                      aria-valuenow={count}
                    >
                      <span
                        className={`dashboard-progress-fill ${ORDER_STATUS_COLORS[status]?.replace("dashboard-status-", "dashboard-progress-") || ""}`}
                        style={{ width: `${share}%` }}
                      ></span>
                    </div>
                  </div>
                );
              })}
              {!Object.keys(orderCounts).length && (
                <div className="dashboard-empty">
                  <p>No order data is available.</p>
                </div>
              )}
            </div>
            <p className="dashboard-data-note">
              Order trends aren’t shown because order creation dates aren’t
              currently recorded.
            </p>
          </section>

          <section className="card dashboard-card dashboard-activity-card">
            <div className="card-header dashboard-section-heading">
              <span>
                <i className="bi bi-clock-history" aria-hidden="true"></i>
                Recent ticket activity
              </span>
              <small>Latest updates</small>
            </div>
            <div className="dashboard-list">
              {overview.recent_activity?.length ? (
                overview.recent_activity.map((activity, index) => (
                  <article
                    className="dashboard-activity-row"
                    key={`${activity.ticket_number}-${activity.occurred_at}-${index}`}
                  >
                    <span
                      className={`dashboard-activity-icon ${activity.type === "status" ? "is-status" : ""}`}
                      aria-hidden="true"
                    >
                      <i
                        className={`bi ${activity.type === "status" ? "bi-arrow-left-right" : "bi-chat-left-text"}`}
                      ></i>
                    </span>
                    <div className="dashboard-activity-copy">
                      <div>
                        <button
                          className="dashboard-ticket-link"
                          onClick={() => onViewTicket(activity.ticket_number)}
                          type="button"
                        >
                          {activity.ticket_number}
                        </button>
                        <span>{activity.description}</span>
                      </div>
                      <p>{activity.subject}</p>
                      <time dateTime={activity.occurred_at}>
                        {formatActivityDate(activity.occurred_at)}
                      </time>
                    </div>
                  </article>
                ))
              ) : (
                <div className="dashboard-empty">
                  <p>No ticket conversations or status changes recorded yet.</p>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}

export default DashboardTab;
