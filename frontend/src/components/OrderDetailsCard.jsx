function OrderDetailsCard({ order }) {
  if (!order) {
    return null;
  }

  return (
    <div className="card mb-3">
      <div className="card-header">Latest Order</div>

      <div className="card-body">
        <p className="ticket-summary-detail">
          <strong className="ticket-summary-field-label">Order Number</strong>
          <span className="ticket-summary-field-value">
            {order.order_number}
          </span>
        </p>

        <p className="ticket-summary-detail">
          <strong className="ticket-summary-field-label">Status</strong>
          <span className="ticket-summary-field-value">{order.status}</span>
        </p>

        <p className="ticket-summary-detail">
          <strong className="ticket-summary-field-label">Amount</strong>
          <span className="ticket-summary-field-value">
            ₹{order.total_amount}
          </span>
        </p>
      </div>
    </div>
  );
}

export default OrderDetailsCard;
