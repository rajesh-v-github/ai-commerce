import { useState, useEffect } from "react";

import { getCustomerOrders } from "../services/customerOrdersService";

import { getOrders } from "../services/orderService";

// Customer order lookup panel used to search orders by username and review the results.
function OrdersByCustomerTab({ token }) {
  const [error, setError] = useState("");

  const [username, setUsername] = useState("");

  const [orders, setOrders] = useState([]);

  const [allOrders, setAllOrders] = useState([]);

  useEffect(() => {
    const loadAllOrders = async () => {
      try {
        const data = await getOrders(token);

        setOrders(data);

        setAllOrders(data);
      } catch (error) {
        console.error(error);
      }
    };

    loadAllOrders();
  }, [token]);

  const loadOrders = async () => {
    if (!username.trim()) {
      setOrders(allOrders);

      setError("");

      return;
    }

    try {
      const data = await getCustomerOrders(username, token);

      if (!data || data.length === 0) {
        setOrders([]);

        setError(`No orders were found for customer '${username}'.`);

        return;
      }

      setError("");

      setOrders(data);
    } catch (error) {
      console.error(error);

      setOrders([]);

      setError(`No customer found with username '${username}'.`);
    }
  };

    const getStatusClass = (status) => {
    switch (status) {
      case "DELIVERED":
        return "badge bg-success";
      case "PROCESSING":
        return "badge bg-warning text-dark";
      case "SHIPPED":
        return "badge bg-info text-dark";
      case "CANCELLED":
        return "badge bg-danger";
      default:
        return "badge bg-secondary";
    }
  };

  return (
    <div>
      <div className="card mb-3">
        <div className="card-header">Search Customer Orders</div>

        <div className="card-body">
          <div className="customer-search-controls">
            <input
              type="text"
              className="form-control"
              placeholder="Enter Customer Username"
              value={username}
              onChange={(e) => {
                const value = e.target.value;
                setUsername(value);
                setError("");
                if (!value.trim()) {
                  setOrders(allOrders);
                  return;
                }

                const filteredOrders = allOrders.filter((order) =>
                  (order.customer_name || "")
                    .toLowerCase()
                    .includes(value.trim().toLowerCase()),
                );
                setOrders(filteredOrders);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  loadOrders();
                }
              }}
            />
            <button
              className="btn btn-primary"
              onClick={loadOrders}
              type="button"
            >
              Search
            </button>
          </div>
          {error && <div className="alert alert-warning mt-3">{error}</div>}
        </div>
      </div>

      <div className="card">
        <div className="card-header">Customer Orders</div>

        <div className="card-body">
          <table className="table table-striped">
            <thead>
              <tr>
                <th>Order Number</th>
                <th>Customer</th>
                <th>Status</th>
                <th>Amount</th>
              </tr>
            </thead>

            <tbody>
              {orders.map((order) => (
                <tr key={order.id}>
                  <td>{order.order_number}</td>

                  <td>{order.customer_name}</td>

                  <td>
                    <span className={getStatusClass(order.status)}>{order.status}</span>
                  </td>

                  <td>₹{order.total_amount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default OrdersByCustomerTab;
