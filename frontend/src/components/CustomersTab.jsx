import { useEffect, useState } from "react";

import { getCustomers } from "../services/customerService";

// Customer lookup workspace used to search, filter, and review customer activity.
function CustomersTab({ token }) {
  // Full customer list returned by the backend.
  const [customers, setCustomers] = useState([]);
  // Search text entered by the support agent.
  const [search, setSearch] = useState("");
  // Filtered subset displayed in the table.
  const [filteredCustomers, setFilteredCustomers] = useState([]);
  // Validation or search feedback shown to the user.
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");

  // Load all customer records when the component mounts or the auth token changes.
  useEffect(() => {
    const loadCustomers = async () => {
      try {
        const data = await getCustomers(token);
        setLoadError("");
        setCustomers(data);
        setFilteredCustomers(data);
      } catch (error) {
        console.error(error);
        setLoadError("Unable to load customers. Please try again.");
      }
    };

    loadCustomers();
  }, [token]);

  // Filter customer records by username and show helpful feedback when no match exists.
  const searchCustomers = () => {
    if (!search.trim()) {
      setFilteredCustomers(customers);
      setError("");
      return;
    }

    const results = customers.filter((customer) =>
      customer.username.toLowerCase().includes(search.toLowerCase()),
    );

    if (results.length === 0) {
      setFilteredCustomers(customers);
      setError(`No customer records found matching '${search}'.`);
      return;
    }

    setError("");
    setFilteredCustomers(results);
  };

  return (
    <div>
      <div className="card mb-3">
        <div className="card-header">Customer Search</div>
        <div className="card-body">
          <div className="customer-search-controls">
            <input
              type="text"
              className="form-control"
              placeholder="Search by username"
              value={search}
              onChange={(e) => {
                const value = e.target.value;
                setSearch(value);
                setError("");

                if (!value.trim()) {
                  setFilteredCustomers(customers);
                  return;
                }

                const results = customers.filter((customer) =>
                  customer.username.toLowerCase().includes(value.toLowerCase()),
                );
                setFilteredCustomers(results);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  searchCustomers();
                }
              }}
            />
            <button
              className="btn btn-primary"
              onClick={searchCustomers}
              type="button"
            >
              Search
            </button>
          </div>

          {error && <div className="alert alert-warning mt-3">{error}</div>}
        </div>
      </div>

      <div className="card">
        <div className="card-header">Customers</div>
        <div className="card-body">
          {loadError && (
            <div className="alert alert-warning" role="alert">
              {loadError}
            </div>
          )}
          <table className="table table-striped table-hover">
            <thead>
              <tr>
                <th>ID</th>
                <th>Username</th>
                <th>Orders</th>
                <th>Tickets</th>
                <th>Open Tickets</th>
              </tr>
            </thead>

            <tbody>
              {!loadError && filteredCustomers.map((customer) => (
                <tr key={customer.customer_id}>
                  <td>{customer.customer_id}</td>
                  <td>{customer.username}</td>
                  <td>{customer.total_orders}</td>
                  <td>{customer.total_tickets}</td>
                  <td>
                    <span className="badge bg-warning">
                      {customer.open_tickets}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default CustomersTab;
