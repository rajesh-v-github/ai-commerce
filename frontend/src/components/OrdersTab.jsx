import { useEffect, useState } from "react";

import { getOrderDetails, getOrders } from "../services/orderService";
import "./OrdersTab.css";

// Orders overview table used to review customer orders and delivery status.
function OrdersTab({
  token,
  selectedOrderNumber = "",
  onClearSelectedOrder,
  onViewOrder,
}) {
  // All orders fetched for the current support workspace.
  const [orders, setOrders] = useState([]);
  const [ordersError, setOrdersError] = useState("");
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

  // Load order records when the component mounts or the auth token changes.
  useEffect(() => {
    const loadOrders = async () => {
      try {
        const data = await getOrders(token);
        setOrdersError("");
        setOrders(data);
      } catch (error) {
        console.error(error);
        setOrdersError("Unable to load orders. Please try again.");
      }
    };

    loadOrders();
  }, [token]);

  useEffect(() => {
    if (!selectedOrderNumber) {
      return;
    }

    let isCurrent = true;
    const loadOrderDetails = async () => {
      setSelectedOrder(null);
      setDetailLoading(true);
      setDetailError("");

      try {
        const order = await getOrderDetails(selectedOrderNumber, token);
        if (isCurrent) {
          setSelectedOrder(order);
        }
      } catch (error) {
        console.error(error);
        if (isCurrent) {
          setDetailError(
            error.response?.status === 404
              ? `Order ${selectedOrderNumber} was not found.`
              : "Unable to load order details. Please try again.",
          );
        }
      } finally {
        if (isCurrent) {
          setDetailLoading(false);
        }
      }
    };

    loadOrderDetails();
    return () => {
      isCurrent = false;
    };
  }, [selectedOrderNumber, token]);

  const normalizedSearch = appliedSearch.trim().toLowerCase();
  const filteredOrders = orders.filter(
    (order) =>
      (order.order_number || "").toLowerCase().includes(normalizedSearch) ||
      (order.customer_name || "").toLowerCase().includes(normalizedSearch),
  );

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

  const formatCurrency = (amount) =>
    new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(amount || 0);

  return (
    <div className="orders-tab">
      {selectedOrderNumber ? (
        <section className="orders-detail-view" aria-labelledby="order-detail-title">
          <div className="orders-detail-toolbar">
            <div>
              <p className="orders-detail-eyebrow">ORDER OVERVIEW</p>
              <h2 id="order-detail-title">Order details</h2>
              <p>Review the order status, customer, and purchased items.</p>
            </div>
            <button
              className="btn btn-outline-secondary orders-back-button"
              onClick={() => {
                setSelectedOrder(null);
                setSearch("");
                setAppliedSearch("");
                onClearSelectedOrder();
              }}
              type="button"
            >
              <i className="bi bi-arrow-left" aria-hidden="true"></i>
              Back to all orders
            </button>
          </div>

          {detailLoading && (
            <div className="orders-detail-state" role="status">
              <span className="spinner-border spinner-border-sm" aria-hidden="true"></span>
              Loading order details...
            </div>
          )}
          {detailError && (
            <div className="alert alert-warning" role="alert">
              {detailError}
            </div>
          )}
          {selectedOrder && (
            <>
              <div className="orders-detail-summary">
                <article className="orders-summary-card orders-summary-number">
                  <span className="orders-summary-icon">
                    <i className="bi bi-receipt" aria-hidden="true"></i>
                  </span>
                  <div>
                    <span className="orders-summary-label">Order number</span>
                    <strong>{selectedOrder.order_number}</strong>
                  </div>
                </article>
                <article className="orders-summary-card">
                  <span className="orders-summary-icon">
                    <i className="bi bi-person" aria-hidden="true"></i>
                  </span>
                  <div>
                    <span className="orders-summary-label">Customer</span>
                    <strong>{selectedOrder.customer_name}</strong>
                  </div>
                </article>
                <article className="orders-summary-card">
                  <span className="orders-summary-icon">
                    <i className="bi bi-activity" aria-hidden="true"></i>
                  </span>
                  <div>
                    <span className="orders-summary-label">Status</span>
                    <span className={getStatusClass(selectedOrder.status)}>
                      {selectedOrder.status}
                    </span>
                  </div>
                </article>
                <article className="orders-summary-card orders-summary-total">
                  <span className="orders-summary-icon">
                    <i className="bi bi-currency-rupee" aria-hidden="true"></i>
                  </span>
                  <div>
                    <span className="orders-summary-label">Order total</span>
                    <strong>{formatCurrency(selectedOrder.total_amount)}</strong>
                  </div>
                </article>
              </div>

              <section className="card orders-items-card">
                <div className="card-header orders-items-heading">
                  <div>
                    <h3>Items in this order</h3>
                    <p>
                      {selectedOrder.items.length}{" "}
                      {selectedOrder.items.length === 1 ? "item" : "items"}
                    </p>
                  </div>
                </div>
                {selectedOrder.items.length ? (
                  <div className="table-responsive">
                    <table className="table orders-items-table">
                      <thead>
                        <tr>
                          <th>Product</th>
                          <th>Quantity</th>
                          <th>Unit price</th>
                          <th className="text-end">Line total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedOrder.items.map((item, index) => (
                          <tr key={`${item.product_id}-${index}`}>
                            <td>
                              <div className="orders-product-main">
                                <span className="orders-product-icon">
                                  <i
                                    className="bi bi-box-seam"
                                    aria-hidden="true"
                                  ></i>
                                </span>
                                <div>
                                  <strong>
                                    {item.product?.name || item.product_name}
                                  </strong>
                                  {item.product?.category && (
                                    <span className="orders-product-category">
                                      {item.product.category}
                                    </span>
                                  )}
                                </div>
                              </div>
                              {item.product?.description && (
                                <p className="orders-product-description">
                                  {item.product.description}
                                </p>
                              )}
                              {item.product && (
                                <p className="orders-product-availability">
                                  <i
                                    className="bi bi-boxes"
                                    aria-hidden="true"
                                  ></i>
                                  <strong>{item.product.stock}</strong>
                                  <span>currently in stock</span>
                                </p>
                              )}
                            </td>
                            <td>
                              <span className="orders-item-quantity">
                                {item.quantity}
                              </span>
                            </td>
                            <td>
                              {formatCurrency(item.unit_price)}
                              {item.product?.current_price != null && (
                                <span className="orders-current-price">
                                  Current catalog:{" "}
                                  {formatCurrency(item.product.current_price)}
                                </span>
                              )}
                            </td>
                            <td className="text-end">
                              <strong>{formatCurrency(item.line_total)}</strong>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr>
                          <td colSpan="3">Order total</td>
                          <td className="text-end">
                            {formatCurrency(selectedOrder.total_amount)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                ) : (
                  <div className="orders-detail-empty">
                    <i className="bi bi-inbox" aria-hidden="true"></i>
                    <p>No item details are available for this order.</p>
                  </div>
                )}
              </section>
            </>
          )}
        </section>
      ) : (
        <>
          <div className="card mb-3">
            <div className="card-header">Order Search</div>
            <div className="card-body">
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
                  placeholder="Search by order number or customer"
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
            </div>
          </div>

          <div className="card">
            <div className="card-header">Customer Orders</div>
            <div className="card-body">
              {ordersError && (
                <div className="alert alert-warning" role="alert">
                  {ordersError}
                </div>
              )}
              <table className="table table-striped table-hover">
                <thead>
                  <tr>
                    <th>Order Number</th>
                    <th>Customer</th>
                    <th>Status</th>
                    <th>Amount</th>
                  </tr>
                </thead>

                <tbody>
                  {ordersError ? (
                    <tr>
                      <td colSpan="4" className="text-center text-muted">
                        Orders could not be loaded.
                      </td>
                    </tr>
                  ) : filteredOrders.length > 0 ? (
                    filteredOrders.map((order) => (
                      <tr key={order.id}>
                        <td>
                          <button
                            className="orders-table-link"
                            onClick={() => onViewOrder(order.order_number)}
                            type="button"
                          >
                            {order.order_number}
                          </button>
                        </td>
                        <td>{order.customer_name}</td>
                        <td>
                          <span className={getStatusClass(order.status)}>
                            {order.status}
                          </span>
                        </td>
                        <td>{formatCurrency(order.total_amount)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="4" className="text-center text-muted">
                        {appliedSearch.trim()
                          ? `No orders found matching "${appliedSearch}".`
                          : "No orders available."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default OrdersTab;
