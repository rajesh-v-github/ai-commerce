import { useEffect, useState } from "react";
import { getTickets } from "../services/ticketService";

function TicketsTab({ token, statusFilter = "", onClearStatusFilter }) {
  const [tickets, setTickets] = useState([]);
  const [loadError, setLoadError] = useState("");
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");

  useEffect(() => {
    const loadTickets = async () => {
      try {
        const data = await getTickets(token);

        setLoadError("");
        setTickets(data);
      } catch (error) {
        console.error(error);
        setLoadError("Unable to load tickets. Please try again.");
      }
    };

    loadTickets();
  }, [token]);

  const filteredTickets = tickets.filter((ticket) => {
    const matchesSearch = (ticket.ticket_number || "")
      .toLowerCase()
      .includes(appliedSearch.trim().toLowerCase());
    const matchesStatus =
      !statusFilter ||
      (ticket.status || "").toUpperCase() === statusFilter.toUpperCase();
    return matchesSearch && matchesStatus;
  });

  return (
    <div>
      <div className="card mb-3">
        <div className="card-header">Ticket Search</div>
        <div className="card-body">
          {statusFilter && (
            <div className="d-flex align-items-center gap-2 mb-3">
              <span className="text-muted">Filtered by status:</span>
              <span className="badge text-bg-primary">
                {statusFilter.replace("_", " ")}
              </span>
              <button
                className="btn btn-sm btn-outline-secondary"
                onClick={onClearStatusFilter}
                type="button"
              >
                Clear filter
              </button>
            </div>
          )}
          {!statusFilter && (
            <form
              className="customer-search-controls"
              onSubmit={(event) => {
                event.preventDefault();
                setAppliedSearch(search);
              }}
            >
              <input
                type="text"
                className="form-control"
                placeholder="Search by ticket number"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setAppliedSearch(event.target.value);
                }}
              />
              <button className="btn btn-primary" type="submit">
                Search
              </button>
            </form>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header">Support Tickets</div>

        <div className="card-body">
          {loadError && (
            <div className="alert alert-warning" role="alert">
              {loadError}
            </div>
          )}
          <table className="table table-striped table-hover">
            <thead>
              <tr>
                <th>Ticket Number</th>
                <th>Subject</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              {loadError ? (
                <tr>
                  <td colSpan="3" className="text-center text-muted">
                    Tickets could not be loaded.
                  </td>
                </tr>
              ) : filteredTickets.length > 0 ? (
                filteredTickets.map((ticket) => (
                  <tr key={ticket.id}>
                    <td>{ticket.ticket_number}</td>
                    <td>{ticket.subject}</td>
                    <td>{ticket.status}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="3" className="text-center text-muted">
                    {appliedSearch.trim()
                      ? `No tickets found matching "${appliedSearch}".`
                      : statusFilter
                        ? `No ${statusFilter.replace("_", " ").toLowerCase()} tickets available.`
                      : "No tickets available."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default TicketsTab;
