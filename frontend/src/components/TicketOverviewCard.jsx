function TicketOverviewCard({ summary }) {
  const getBadgeColor = (status) => {
    switch (status) {
      case "OPEN":
        return "bg-warning";

      case "IN_PROGRESS":
        return "bg-primary";

      case "RESOLVED":
        return "bg-success";

      case "CLOSED":
        return "bg-secondary";

      default:
        return "bg-dark";
    }
  };

  return (
    <div className="card mb-3">
      <div className="card-header">Ticket Overview</div>

      <div className="card-body">
        <h5>{summary.ticket_number}</h5>

        <p className="ticket-summary-detail">
          <strong className="ticket-summary-field-label">Subject</strong>
          <span className="ticket-summary-field-value">{summary.subject}</span>
        </p>

        <p className="ticket-summary-detail">
          <strong className="ticket-summary-field-label">Priority</strong>
          <span className="ticket-summary-field-value">{summary.priority}</span>
        </p>

        <span className={`badge ${getBadgeColor(summary.status)}`}>
          {summary.status}
        </span>
      </div>
    </div>
  );
}

export default TicketOverviewCard;
