function TicketTimeline({ history }) {
  if (!history) {
    return null;
  }

  return (
    <div className="card mb-3">
      <div className="card-header">Ticket Timeline</div>

      <div className="card-body">
        {history.length === 0 ? (
          <p className="ticket-timeline-empty">
            No status changes have been recorded for this ticket yet.
          </p>
        ) : (
          history.map((item) => (
            <div key={item.id} className="mb-2">
              <strong>{item.old_status}</strong>
              {" -> "}
              <strong>{item.new_status}</strong>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default TicketTimeline;
