import { useCallback, useEffect, useState } from "react";
import { useToast } from "../context/toastContextObject";
import {
  createAdminCustomer,
  fetchAdminCustomerDetail,
  fetchAdminCustomers,
  updateAdminCustomer,
} from "../services/adminService";
import { formatDateTime, formatINR } from "../utils/formatters";

const EMPTY_CUSTOMER_FORM = {
  username: "",
  full_name: "",
  email: "",
  phone: "",
  shipping_address: "",
  billing_address: "",
  password: "",
  is_active: true,
};

function AdminCustomersSection() {
  const { showToast } = useToast();

  const [customers, setCustomers] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Add / Edit modal
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [form, setForm] = useState(EMPTY_CUSTOMER_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  // Customer 360 profile modal
  const [profileCustomer, setProfileCustomer] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);

  const loadCustomers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchAdminCustomers({
        search: search.trim() || undefined,
        status_filter: statusFilter,
      });
      setCustomers(data.customers || data.items || []);
      setTotalCount(data.total || 0);
    } catch (err) {
      console.error(err);
      showToast("Failed to load customer directory.", "danger");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, showToast]);

  useEffect(() => {
    let active = true;
    const fetchCustomers = async () => {
      try {
        const data = await fetchAdminCustomers({
          search: search.trim() || undefined,
          status_filter: statusFilter,
        });
        if (active) {
          setCustomers(data.customers || data.items || []);
          setTotalCount(data.total || 0);
        }
      } catch (err) {
        console.error(err);
        if (active) {
          showToast("Failed to load customer directory.", "danger");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    fetchCustomers();
    return () => {
      active = false;
    };
  }, [search, statusFilter, showToast]);

  const openAddModal = () => {
    setEditingCustomer(null);
    setForm(EMPTY_CUSTOMER_FORM);
    setFormError("");
    setFormModalOpen(true);
  };

  const openEditModal = (cust) => {
    setEditingCustomer(cust);
    setForm({
      username: cust.username || "",
      full_name: cust.full_name || "",
      email: cust.email || "",
      phone: cust.phone || "",
      shipping_address: cust.shipping_address || "",
      billing_address: cust.billing_address || "",
      password: "",
      is_active: cust.is_active !== false,
    });
    setFormError("");
    setFormModalOpen(true);
  };

  const handleSaveCustomer = async (e) => {
    e.preventDefault();
    setFormError("");
    try {
      setSaving(true);
      if (editingCustomer) {
        const payload = {
          full_name: form.full_name.trim(),
          email: form.email.trim(),
          phone: form.phone.trim() || null,
          shipping_address: form.shipping_address.trim() || null,
          billing_address: form.billing_address.trim() || null,
          is_active: Boolean(form.is_active),
        };
        if (form.password.trim()) {
          payload.password = form.password.trim();
        }
        await updateAdminCustomer(editingCustomer.id, payload);
        showToast(`Customer "${form.full_name}" updated.`, "success");
      } else {
        const derivedUsername =
          form.username.trim() ||
          form.email
            .trim()
            .split("@")[0]
            .replace(/[^A-Za-z0-9_.-]/g, "_")
            .slice(0, 32) ||
          `cust_${Date.now().toString().slice(-6)}`;
        await createAdminCustomer({
          username: derivedUsername,
          full_name: form.full_name.trim(),
          email: form.email.trim(),
          phone: form.phone.trim() || null,
          shipping_address: form.shipping_address.trim() || null,
          billing_address: form.billing_address.trim() || null,
          password: form.password.trim() || undefined,
        });
        showToast(`Customer "${form.full_name}" added.`, "success");
      }
      setFormModalOpen(false);
      await loadCustomers();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setFormError(
        typeof detail === "string"
          ? detail
          : "Unable to save customer. Verify email/username uniqueness.",
      );
    } finally {
      setSaving(false);
    }
  };

  const openCustomer360 = async (cust) => {
    try {
      setLoadingProfile(true);
      setProfileCustomer({ customer: cust, orders: [], tickets: [] });
      const detail = await fetchAdminCustomerDetail(cust.id);
      setProfileCustomer(detail);
    } catch (err) {
      console.error(err);
      showToast("Failed to load customer 360° profile.", "danger");
    } finally {
      setLoadingProfile(false);
    }
  };

  return (
    <div className="d-grid gap-4">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
        <div>
          <h1 className="fs-3 fw-bold mb-1">Customer Directory &amp; CRM</h1>
          <p className="text-muted small mb-0">
            View customer profiles, purchase activity, lifetime spend, and
            deduplicated repeat-checkout records ({totalCount} customers)
          </p>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          onClick={openAddModal}
        >
          <i className="bi bi-person-plus-fill me-1"></i>
          Add Customer
        </button>
      </div>

      {/* Search & Filter */}
      <div className="adm-card">
        <div className="row g-2 align-items-center">
          <div className="col-md-8">
            <div className="input-group input-group-sm">
              <span className="input-group-text bg-white">
                <i className="bi bi-search"></i>
              </span>
              <input
                type="search"
                className="form-control"
                placeholder="Search customer by name, username, email, or phone..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          <div className="col-md-4">
            <select
              className="form-select form-select-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Customer Accounts</option>
              <option value="active">Active Accounts Only</option>
              <option value="inactive">Inactive / Suspended</option>
            </select>
          </div>
        </div>
      </div>

      {/* Customers Table */}
      <div className="adm-card p-0 overflow-hidden">
        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border text-primary" role="status"></div>
          </div>
        ) : customers.length === 0 ? (
          <div className="text-center py-5">
            <p className="text-muted mb-0">
              No customers match your search criteria.
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table adm-table table-hover mb-0">
              <thead>
                <tr>
                  <th className="ps-4">Customer</th>
                  <th>Contact</th>
                  <th className="text-center">Orders</th>
                  <th className="text-end">Lifetime Spend</th>
                  <th>Last Purchase</th>
                  <th>Status</th>
                  <th className="text-end pe-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((cust) => (
                  <tr key={cust.id}>
                    <td className="ps-4">
                      <div className="fw-bold">
                        {cust.full_name || cust.username}
                      </div>
                      <div className="text-muted font-monospace small">
                        @{cust.username}
                      </div>
                    </td>
                    <td>
                      <div className="small">{cust.email || "—"}</div>
                      <div className="text-muted small">{cust.phone || "—"}</div>
                    </td>
                    <td className="text-center">
                      <span className="badge bg-light text-dark border">
                        {cust.total_orders ?? cust.order_count ?? 0}
                      </span>
                    </td>
                    <td className="text-end fw-bold">
                      {formatINR(cust.lifetime_spend ?? cust.total_spent ?? 0)}
                    </td>
                    <td className="small text-muted">
                      {cust.last_order_at
                        ? formatDateTime(cust.last_order_at)
                        : "No orders yet"}
                    </td>
                    <td>
                      {cust.is_active ? (
                        <span className="badge bg-success-subtle text-success">
                          Active
                        </span>
                      ) : (
                        <span className="badge bg-secondary-subtle text-secondary">
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="text-end pe-4">
                      <div className="btn-group btn-group-sm">
                        <button
                          type="button"
                          className="btn btn-outline-primary"
                          onClick={() => openCustomer360(cust)}
                        >
                          360° Profile
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-secondary"
                          onClick={() => openEditModal(cust)}
                        >
                          Edit
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add / Edit Customer Modal */}
      {formModalOpen && (
        <div className="adm-modal-backdrop" role="dialog" aria-modal="true">
          <form className="adm-modal-dialog" onSubmit={handleSaveCustomer}>
            <div className="adm-modal-header">
              <h2 className="fs-5 fw-bold mb-0">
                {editingCustomer
                  ? `Edit Customer: ${editingCustomer.full_name || editingCustomer.username}`
                  : "Add New Customer"}
              </h2>
              <button
                type="button"
                className="btn-close"
                onClick={() => setFormModalOpen(false)}
              />
            </div>

            <div className="adm-modal-body d-grid gap-3">
              {formError && (
                <div className="alert alert-danger py-2 small mb-0">
                  {formError}
                </div>
              )}

              <div className="row g-3">
                <div className="col-md-6">
                  <label className="form-label small fw-semibold">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    value={form.full_name}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        full_name: e.target.value,
                      }))
                    }
                  />
                </div>

                {!editingCustomer && (
                  <div className="col-md-6">
                    <label className="form-label small fw-semibold">
                      Username (Optional — auto-derived if blank)
                    </label>
                    <input
                      type="text"
                      className="form-control font-monospace"
                      value={form.username}
                      onChange={(e) =>
                        setForm((prev) => ({
                          ...prev,
                          username: e.target.value,
                        }))
                      }
                    />
                  </div>
                )}

                <div className="col-md-6">
                  <label className="form-label small fw-semibold">
                    Email Address *
                  </label>
                  <input
                    type="email"
                    className="form-control"
                    required
                    value={form.email}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, email: e.target.value }))
                    }
                  />
                </div>

                <div className="col-md-6">
                  <label className="form-label small fw-semibold">
                    Phone Number
                  </label>
                  <input
                    type="tel"
                    className="form-control"
                    value={form.phone}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, phone: e.target.value }))
                    }
                  />
                </div>

                <div className="col-12">
                  <label className="form-label small fw-semibold">
                    Shipping Address
                  </label>
                  <textarea
                    rows="2"
                    className="form-control"
                    value={form.shipping_address}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        shipping_address: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="col-12">
                  <label className="form-label small fw-semibold">
                    Billing Address
                  </label>
                  <textarea
                    rows="2"
                    className="form-control"
                    value={form.billing_address}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        billing_address: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="col-md-6">
                  <label className="form-label small fw-semibold">
                    {editingCustomer
                      ? "Reset Password (Optional, min 8 chars)"
                      : "Initial Password (Optional, min 8 chars)"}
                  </label>
                  <input
                    type="password"
                    minLength={8}
                    className="form-control"
                    value={form.password}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, password: e.target.value }))
                    }
                    placeholder="Leave blank unless setting password"
                  />
                </div>

                {editingCustomer && (
                  <div className="col-md-6 d-flex align-items-end">
                    <div className="form-check mb-2">
                      <input
                        id="cust-active-chk"
                        type="checkbox"
                        className="form-check-input"
                        checked={form.is_active}
                        onChange={(e) =>
                          setForm((prev) => ({
                            ...prev,
                            is_active: e.target.checked,
                          }))
                        }
                      />
                      <label
                        className="form-check-label small fw-semibold"
                        htmlFor="cust-active-chk"
                      >
                        Customer account is active
                      </label>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="adm-modal-footer">
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={() => setFormModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={saving}
              >
                {saving
                  ? "Saving..."
                  : editingCustomer
                    ? "Save Customer"
                    : "Create Customer"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Customer 360 Profile Modal */}
      {profileCustomer && (
        <div className="adm-modal-backdrop" role="dialog" aria-modal="true">
          <div className="adm-modal-dialog" style={{ maxWidth: "820px" }}>
            <div className="adm-modal-header">
              <div>
                <h2 className="fs-5 fw-bold mb-0">
                  {profileCustomer.customer.full_name ||
                    profileCustomer.customer.username}
                </h2>
                <p className="text-muted small mb-0">
                  @{profileCustomer.customer.username} •{" "}
                  {profileCustomer.customer.email || "No email"} •{" "}
                  {profileCustomer.customer.phone || "No phone"}
                </p>
              </div>
              <button
                type="button"
                className="btn-close"
                onClick={() => setProfileCustomer(null)}
              />
            </div>

            <div className="adm-modal-body d-grid gap-4">
              {loadingProfile && (
                <div className="text-center py-2">
                  <span className="spinner-border spinner-border-sm text-primary me-2"></span>
                  <span className="small text-muted">
                    Loading order &amp; support history...
                  </span>
                </div>
              )}

              <div className="row g-3">
                <div className="col-md-4">
                  <div className="border rounded-3 p-3 bg-light">
                    <div className="small text-muted">Lifetime Spend</div>
                    <div className="fs-4 fw-bold">
                      {formatINR(
                        profileCustomer.customer.lifetime_spend ??
                          profileCustomer.customer.total_spent ??
                          0,
                      )}
                    </div>
                  </div>
                </div>
                <div className="col-md-4">
                  <div className="border rounded-3 p-3 bg-light">
                    <div className="small text-muted">Total Orders</div>
                    <div className="fs-4 fw-bold">
                      {profileCustomer.customer.total_orders ??
                        profileCustomer.customer.order_count ??
                        0}
                    </div>
                  </div>
                </div>
                <div className="col-md-4">
                  <div className="border rounded-3 p-3 bg-light">
                    <div className="small text-muted">Support Tickets</div>
                    <div className="fs-4 fw-bold">
                      {profileCustomer.tickets?.length || 0}
                    </div>
                  </div>
                </div>
              </div>

              {profileCustomer.customer.shipping_address && (
                <div className="border rounded-3 p-3 small">
                  <strong>Saved Shipping Address:</strong>{" "}
                  {profileCustomer.customer.shipping_address}
                </div>
              )}

              <div>
                <h3 className="fs-6 fw-bold mb-2">Order History</h3>
                {profileCustomer.orders?.length === 0 ? (
                  <p className="text-muted small">
                    No orders placed by this customer yet.
                  </p>
                ) : (
                  <div className="border rounded-3 overflow-hidden">
                    <table className="table table-sm align-middle mb-0">
                      <thead className="table-light">
                        <tr>
                          <th className="ps-3">Order #</th>
                          <th>Date</th>
                          <th>Items</th>
                          <th>Status</th>
                          <th className="text-end pe-3">Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        {profileCustomer.orders.map((ord) => (
                          <tr key={ord.id}>
                            <td className="ps-3 font-monospace fw-bold">
                              {ord.order_number}
                            </td>
                            <td className="small text-muted">
                              {formatDateTime(ord.created_at)}
                            </td>
                            <td>{ord.item_count}</td>
                            <td>
                              <span className="badge bg-light text-dark border">
                                {ord.status}
                              </span>
                            </td>
                            <td className="text-end fw-bold pe-3">
                              {formatINR(ord.total_amount)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div>
                <h3 className="fs-6 fw-bold mb-2">Support Tickets</h3>
                {profileCustomer.tickets?.length === 0 ? (
                  <p className="text-muted small mb-0">
                    No support tickets filed for this customer.
                  </p>
                ) : (
                  <div className="border rounded-3 overflow-hidden">
                    <table className="table table-sm align-middle mb-0">
                      <thead className="table-light">
                        <tr>
                          <th className="ps-3">Ticket #</th>
                          <th>Subject</th>
                          <th>Priority</th>
                          <th className="pe-3">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {profileCustomer.tickets.map((tk) => (
                          <tr key={tk.id}>
                            <td className="ps-3 font-monospace">
                              {tk.ticket_number}
                            </td>
                            <td>{tk.subject}</td>
                            <td>{tk.priority}</td>
                            <td className="pe-3">{tk.status}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

            <div className="adm-modal-footer">
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={() => setProfileCustomer(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminCustomersSection;
