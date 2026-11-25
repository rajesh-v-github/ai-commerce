import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getStoredToken } from "../services/authStorage";
import {
  getDashboardData,
  runAssistantFeature,
} from "../services/copilotService";
import { getOverview } from "../services/dashboardService";
import { getCustomers } from "../services/customerService";
import TicketOverviewCard from "../components/TicketOverviewCard";
import OrderDetailsCard from "../components/OrderDetailsCard";
import TicketTimeline from "../components/TicketTimeline";
import ConversationHistoryCard from "../components/ConversationHistoryCard";
import DraftResponseCard from "../components/DraftResponseCard";
import loadingGif from "../assets/loading.gif";
import TicketsTab from "../components/TicketsTab";
import ProductsTab from "../components/ProductsTab";
import OrdersTab from "../components/OrdersTab";
// import OrdersByCustomerTab from "../components/OrdersByCustomerTab";
import CustomersTab from "../components/CustomersTab";
import DashboardTab from "../components/DashboardTab";
import { createTicket, getTickets } from "../services/ticketService";
import soranoLogo from "../assets/sorano-logo.png";
import "./CopilotPage.css";

const ASSISTANT_FEATURES = [
  {
    id: "order_lookup",
    label: "Order Lookup",
    description: "Answer questions about a customer's orders.",
    icon: "bi-bag-check",
  },
  {
    id: "product_lookup",
    label: "Product Lookup",
    description: "Find product details, pricing, and availability.",
    icon: "bi-search",
  },
  {
    id: "product_recommendation",
    label: "Product Recommendations",
    description: "Match available products to customer needs.",
    icon: "bi-stars",
  },
  {
    id: "ticket_summary",
    label: "Ticket Summary",
    description: "Review ticket insights and recommended actions.",
    icon: "bi-ticket-detailed",
  },
  {
    id: "create_ticket",
    label: "Create Ticket",
    description: "Draft and create a customer support ticket.",
    icon: "bi-plus-square",
  },
];

// Convert the assistant's text response into order cards when it includes
// recognizable order headings and labeled details.
function formatOrderLookupResponse(response) {
  const lines = response
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !/^[=*_—-]{3,}$/.test(line))
    .map((line) =>
      line.replace(/^(?:(?:\d+[.)])|[-*])\s*/, "").replace(/^\*\*(.*)\*\*$/, "$1"),
    );
  const orders = [];
  const introduction = [];
  let currentOrder = null;

  for (const line of lines) {
    const headingMatch = line.match(
      /^(?:Order\s+Details\s+for\s+|Order(?:\s+\d+)?\s*:\s*|Order\s+#)([A-Z0-9][A-Z0-9_-]*)\s*$/i,
    );

    if (headingMatch) {
      const orderNumber = headingMatch[1];
      currentOrder = orders.find((order) => order.orderNumber === orderNumber);

      if (!currentOrder) {
        currentOrder = { orderNumber, details: [] };
        orders.push(currentOrder);
      }
      continue;
    }

    const fieldMatch = line.match(/^([^:]+):\s*(.+)$/);
    if (!fieldMatch) {
      if (currentOrder) {
        currentOrder.details.push({ label: "Details", value: line });
      } else {
        introduction.push(line);
      }
      continue;
    }

    const label = fieldMatch[1].trim();
    const value = fieldMatch[2].trim();

    if (/^order\s+number$/i.test(label)) {
      currentOrder = orders.find((order) => order.orderNumber === value);
      if (!currentOrder) {
        currentOrder = { orderNumber: value, details: [] };
        orders.push(currentOrder);
      }
      continue;
    }

    if (currentOrder) {
      currentOrder.details.push({ label, value });
    } else {
      introduction.push(`${label}: ${value}`);
    }
  }

  return {
    orders: orders.filter((order) => order.details.length > 0),
    introduction: introduction.join(" "),
    cleanedText: lines.join("\n"),
  };
}

// Convert varied product-response formats into consistent product result cards.
function formatProductLookupResponse(response) {
  const lines = response
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !/^[=*_—-]{3,}$/.test(line));
  const products = [];
  const introduction = [];
  const pendingText = [];
  let currentProduct = null;
  const fieldPattern =
    /^(Category|Price|Stock|Availability|Description|Reason|Match)\s*:\s*(.*)$/i;

  const normalizeLine = (rawLine) =>
    rawLine
      .replace(/^(?:[-*•]|\d+[.)])\s+/, "")
      .replace(/^\*\*(.*?)\*\*/, "$1")
      .replace(/\*\*/g, "")
      .trim();

  const addProduct = (name) => {
    currentProduct = { name, details: [] };
    products.push(currentProduct);
  };

  for (let index = 0; index < lines.length; index += 1) {
    const rawLine = lines[index];
    let line = normalizeLine(rawLine);
    const productHeading = line.match(
      /^(?:Product(?:\s+\d+)?|Product\s+Name|Name)\s*:\s*(.+)$/i,
    );
    const boldProduct = rawLine.match(
      /^(?:[-*•]|\d+[.)])?\s*\*\*(.+?)\*\*\s*[:—-]\s*(.*)$/,
    );

    if (productHeading || boldProduct) {
      const name = productHeading
        ? productHeading[1].trim()
        : boldProduct[1].trim();
      addProduct(name);
      const remainder = boldProduct?.[2]?.trim();
      if (productHeading) {
        continue;
      } else if (remainder) {
        line = remainder;
      } else {
        continue;
      }
    }

    const fieldMatch = line.match(fieldPattern);
    if (fieldMatch) {
      if (!currentProduct && pendingText.length > 0) {
        const name = pendingText.pop();
        introduction.push(...pendingText.splice(0));
        addProduct(name);
      }
      if (currentProduct) {
        currentProduct.details.push({
          label: fieldMatch[1],
          value: /^(?:none|null|n\/a|not available)$/i.test(
            fieldMatch[2].trim(),
          )
            ? "Not specified"
            : fieldMatch[2].trim() || "Not specified",
        });
      } else {
        introduction.push(line);
      }
      continue;
    }

    if (!line) {
      continue;
    }

    const nextLine = lines[index + 1]
      ? normalizeLine(lines[index + 1])
      : "";
    const nextLineIsField = fieldPattern.test(nextLine);
    const hasProductMetadata = currentProduct?.details.some((detail) =>
      ["Category", "Price", "Stock", "Availability", "Reason", "Match"].includes(
        detail.label,
      ),
    );

    if (nextLineIsField) {
      if (hasProductMetadata) {
        addProduct(line);
      } else if (!currentProduct) {
        pendingText.push(line);
      } else {
        currentProduct.details.push({ label: "Description", value: line });
      }
    } else if (currentProduct) {
      currentProduct.details.push({ label: "Description", value: line });
    } else {
      pendingText.push(line);
    }
  }

  introduction.push(...pendingText);

  return {
    products: products.filter((product) => product.name),
    introduction: introduction.join(" "),
    cleanedText: lines
      .map(normalizeLine)
      .join("\n"),
  };
}

function CopilotPage({ onLogout }) {
  // Ticket number selected for AI-driven support analysis.
  const [ticketNumber, setTicketNumber] = useState("");
  // Response payload returned from the backend for the chosen ticket.
  const [dashboard, setDashboard] = useState(null);
  // Loading state while the dashboard data is being fetched.
  const [loading, setLoading] = useState(false);
  // Summary metrics shown on the main executive dashboard.
  const [overview, setOverview] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState("");
  const [ticketStatusFilter, setTicketStatusFilter] = useState("");
  const [selectedOrderNumber, setSelectedOrderNumber] = useState("");
  // Navigation state for the support workspace tabs.
  const [activeTab, setActiveTab] = useState("dashboard");
  // Keep the existing Order Lookup dashboard as the default AI Assistant feature.
  const [assistantFeature, setAssistantFeature] = useState("order_lookup");
  const [assistantQuestion, setAssistantQuestion] = useState("");
  const [assistantCustomerId, setAssistantCustomerId] = useState("");
  const [assistantCustomers, setAssistantCustomers] = useState([]);
  const [assistantCustomerLoading, setAssistantCustomerLoading] =
    useState(true);
  const [assistantTickets, setAssistantTickets] = useState([]);
  const [ticketSummaryError, setTicketSummaryError] = useState("");
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantResponse, setAssistantResponse] = useState("");
  const [assistantError, setAssistantError] = useState("");
  const [ticketPreview, setTicketPreview] = useState(null);
  const [ticketCreateLoading, setTicketCreateLoading] = useState(false);
  const [ticketCreated, setTicketCreated] = useState(null);

  const token = getStoredToken();

  const normalizeTicketInput = (rawValue) => {
    const trimmed = (rawValue || "").trim().toUpperCase();
    if (!trimmed) {
      return "";
    }
    if (/^\d+$/.test(trimmed)) {
      return `TKT-${trimmed.padStart(3, "0")}`;
    }
    return trimmed;
  };

  // Fetch AI support analysis for the selected ticket and update the dashboard view.
  const loadDashboard = async (overrideNumber) => {
    const targetInput =
      typeof overrideNumber === "string" ? overrideNumber : ticketNumber;
    const normalizedTicket = normalizeTicketInput(targetInput);
    if (!normalizedTicket) {
      setTicketSummaryError(
        "Enter or select a ticket number first (for example, TKT-001).",
      );
      return;
    }

    try {
      setLoading(true);
      setTicketSummaryError("");
      setTicketNumber(normalizedTicket);
      const result = await getDashboardData(normalizedTicket, token);
      setDashboard(result);
    } catch (error) {
      console.error(error);
      if (error.response?.status !== 401) {
        setDashboard(null);
        setTicketSummaryError(
          error.response?.status === 404
            ? `Ticket ${normalizedTicket} was not found. Please check the ticket number and try again.`
            : "Unable to generate ticket summary right now. Please try again.",
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const clearTicketSummary = () => {
    setTicketNumber("");
    setTicketSummaryError("");
    setDashboard(null);
  };

  const loadOverview = useCallback(async () => {
    try {
      setOverviewLoading(true);
      setOverviewError("");
      const result = await getOverview(token);
      setOverview(result);
    } catch (error) {
      console.error(error);
      if (error.response?.status !== 401) {
        setOverviewError("Unable to load dashboard data. Please try again.");
      }
    } finally {
      setOverviewLoading(false);
    }
  }, [token]);

  // Load workspace summary cards when the page is opened or the auth token changes.
  useEffect(() => {
    let isCurrent = true;

    const initializeOverview = async () => {
      try {
        const result = await getOverview(token);
        if (isCurrent) {
          setOverview(result);
          setOverviewError("");
        }
      } catch (error) {
        console.error(error);
        if (isCurrent && error.response?.status !== 401) {
          setOverviewError("Unable to load dashboard data. Please try again.");
        }
      } finally {
        if (isCurrent) {
          setOverviewLoading(false);
        }
      }
    };

    initializeOverview();
    return () => {
      isCurrent = false;
    };
  }, [token]);

  // Preload customer and ticket directories so Order Lookup, Create Ticket,
  // and Ticket Summary dropdowns are immediately populated on first visit.
  useEffect(() => {
    if (!token) {
      return;
    }
    let isCurrent = true;

    const loadAssistantDirectories = async () => {
      try {
        const [customersData, ticketsData] = await Promise.all([
          getCustomers(token),
          getTickets(token).catch(() => []),
        ]);
        if (isCurrent) {
          setAssistantCustomers(Array.isArray(customersData) ? customersData : []);
          setAssistantTickets(Array.isArray(ticketsData) ? ticketsData : []);
        }
      } catch (error) {
        console.error(error);
      } finally {
        if (isCurrent) {
          setAssistantCustomerLoading(false);
        }
      }
    };

    loadAssistantDirectories();
    return () => {
      isCurrent = false;
    };
  }, [token]);

  const handleDashboardTicketFilter = (status) => {
    setTicketStatusFilter(status || "");
    setActiveTab("tickets");
  };

  const handleDashboardViewTicket = (number) => {
    setTicketNumber(number);
    setAssistantFeature("ticket_summary");
    setActiveTab("copilot");
    loadDashboard(number);
  };

  const handleDashboardViewOrder = (orderNumber) => {
    setSelectedOrderNumber(orderNumber);
    setActiveTab("orders");
  };

  const handleAssistantFeatureChange = async (feature) => {
    setAssistantFeature(feature);
    setAssistantQuestion("");
    setAssistantResponse("");
    setAssistantError("");
    setTicketPreview(null);
    setTicketCreated(null);

    if (
      !["order_lookup", "create_ticket"].includes(feature) ||
      assistantCustomers.length > 0 ||
      assistantCustomerLoading
    ) {
      return;
    }

    // Load the customer list only for assistant tools that need a customer choice.
    try {
      setAssistantCustomerLoading(true);
      const customers = await getCustomers(token);
      setAssistantCustomers(customers);
    } catch (error) {
      console.error(error);
      setAssistantError("Unable to load customers. Please try again.");
    } finally {
      setAssistantCustomerLoading(false);
    }
  };

  const resetOrderLookup = () => {
    setAssistantCustomerId("");
    setAssistantQuestion("");
    setAssistantResponse("");
    setAssistantError("");
  };

  const resetProductAssistant = () => {
    setAssistantQuestion("");
    setAssistantResponse("");
    setAssistantError("");
  };

  const resetTicketCreation = () => {
    setAssistantCustomerId("");
    setAssistantQuestion("");
    setAssistantError("");
    setTicketPreview(null);
    setTicketCreated(null);
  };

  const runSelectedAssistantFeature = async () => {
    if (!assistantQuestion.trim()) {
      setAssistantError("Enter a question or customer requirement first.");
      return;
    }

    if (
      ["order_lookup", "create_ticket"].includes(assistantFeature) &&
      !assistantCustomerId
    ) {
      setAssistantError(
        assistantFeature === "create_ticket"
          ? "Select the customer this ticket is for."
          : "Select a customer to look up their orders.",
      );
      return;
    }

    try {
      setAssistantLoading(true);
      setAssistantError("");
      setAssistantResponse("");
      if (assistantFeature === "create_ticket") {
        setTicketPreview(null);
        setTicketCreated(null);
      }

      // Ticket creation first generates an editable draft; the separate submit
      // action persists it only after the executive reviews the details.
      const request = {
        feature: assistantFeature,
        question: assistantQuestion.trim(),
        ...(assistantFeature === "order_lookup"
          ? { customer_id: Number(assistantCustomerId) }
          : {}),
      };
      const result = await runAssistantFeature(request, token);
      if (assistantFeature === "create_ticket") {
        const draft = result.ticket_preview;
        if (
          !draft ||
          typeof draft.subject !== "string" ||
          !draft.subject.trim() ||
          typeof draft.description !== "string" ||
          !draft.description.trim()
        ) {
          throw new Error("The assistant returned an invalid ticket draft.");
        }
        const generatedPriority =
          typeof draft.priority === "string"
            ? draft.priority.toUpperCase()
            : "";
        setTicketPreview({
          subject: draft.subject,
          description: draft.description,
          priority: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].includes(
            generatedPriority,
          )
            ? generatedPriority
            : "MEDIUM",
        });
        return;
      }

      const responseText =
        assistantFeature === "product_recommendation"
          ? result.recommendation
          : result.answer;

      if (typeof responseText !== "string" || !responseText.trim()) {
        throw new Error("The assistant returned an empty response.");
      }

      setAssistantResponse(responseText);
    } catch (error) {
      console.error(error);
      setAssistantError(
        "Unable to complete this request. Please review your input and try again.",
      );
    } finally {
      setAssistantLoading(false);
    }
  };

  const submitTicket = async () => {
    if (!ticketPreview || !assistantCustomerId) {
      setAssistantError("Choose a customer and prepare a ticket draft first.");
      return;
    }

    try {
      setTicketCreateLoading(true);
      setAssistantError("");
      // Assign the reviewed ticket to the explicitly selected customer.
      const created = await createTicket(
        {
          ...ticketPreview,
          customer_id: Number(assistantCustomerId),
        },
        token,
      );
      setTicketCreated(created);
      setTicketPreview(null);
      setAssistantQuestion("");
      const updatedTickets = await getTickets(token).catch(() => null);
      if (Array.isArray(updatedTickets)) {
        setAssistantTickets(updatedTickets);
      }
      await loadOverview();
    } catch (error) {
      console.error(error);
      const detail = error.response?.data?.detail;
      setAssistantError(
        typeof detail === "string"
          ? detail
          : "Unable to create the ticket. Please review the details and try again.",
      );
    } finally {
      setTicketCreateLoading(false);
    }
  };

  return (
    <div className="executive-workspace">
      {/* Centered brand header anchors the support workspace. */}
      <header className="workspace-header">
        <img
          className="workspace-company-logo"
          src={soranoLogo}
          alt="SoranoTech"
        />
        <div className="workspace-brand">
          <div className="workspace-logo" aria-hidden="true">
            <i className="bi bi-headset"></i>
          </div>
          <div className="workspace-brand-copy">
            <p className="workspace-eyebrow">CUSTOMER EXPERIENCE OPERATIONS</p>
            <h1>Customer Support</h1>
            <p className="workspace-subtitle">
              Executive workspace <span aria-hidden="true">·</span> Service
              with clarity and care
            </p>
          </div>
        </div>

        <button
          className="btn workspace-logout"
          onClick={onLogout}
          aria-label="Log out"
        >
          <i className="bi bi-box-arrow-right" aria-hidden="true"></i>
          Logout
        </button>
      </header>

      {/* Navigate between the operational dashboard and support data views. */}
      <ul className="nav nav-tabs workspace-nav">
        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === "dashboard" ? "active" : ""}`}
            onClick={() => setActiveTab("dashboard")}
          >
            <i className="bi bi-grid-1x2" aria-hidden="true"></i>
            Dashboard
          </button>
        </li>

        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === "copilot" ? "active" : ""}`}
            onClick={() => setActiveTab("copilot")}
          >
            <i className="bi bi-stars" aria-hidden="true"></i>
            AI Assistant
          </button>
        </li>

        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === "orders" ? "active" : ""}`}
            onClick={() => {
              setSelectedOrderNumber("");
              setActiveTab("orders");
            }}
          >
            <i className="bi bi-bag" aria-hidden="true"></i>
            All Orders
          </button>
        </li>

        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === "products" ? "active" : ""}`}
            onClick={() => setActiveTab("products")}
          >
            <i className="bi bi-box-seam" aria-hidden="true"></i>
            Products
          </button>
        </li>

        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === "tickets" ? "active" : ""}`}
            onClick={() => {
              setTicketStatusFilter("");
              setActiveTab("tickets");
            }}
          >
            <i className="bi bi-ticket-perforated" aria-hidden="true"></i>
            Tickets
          </button>
        </li>
        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === "customers" ? "active" : ""}`}
            onClick={() => setActiveTab("customers")}
          >
            <i className="bi bi-people" aria-hidden="true"></i>
            Customers
          </button>
        </li>
        <li className="nav-item ms-auto d-flex align-items-center gap-2 py-1">
          <Link
            to="/admin"
            className="btn btn-sm btn-outline-primary d-inline-flex align-items-center gap-1"
          >
            <i className="bi bi-speedometer2" aria-hidden="true"></i>
            Admin Dashboard
          </Link>
          <Link
            to="/"
            className="btn btn-sm btn-outline-secondary d-inline-flex align-items-center gap-1"
          >
            <i className="bi bi-shop" aria-hidden="true"></i>
            Storefront
          </Link>
        </li>
        {/* <li className="nav-item">
          <button
            className={`nav-link ${
              activeTab === "ordersByCustomer" ? "active" : ""
            }`}
            onClick={() => setActiveTab("ordersByCustomer")}
          >
            <i className="bi bi-person-lines-fill" aria-hidden="true"></i>
            Orders By Customer
          </button>
        </li> */}
      </ul>

      <main className="workspace-content">
        {/* Operational overview with ticket, activity, and order summaries. */}
        {activeTab === "dashboard" && (
          <DashboardTab
            overview={overview}
            loading={overviewLoading}
            error={overviewError}
            onRetry={loadOverview}
            onFilterTickets={handleDashboardTicketFilter}
            onViewTicket={handleDashboardViewTicket}
            onViewOrder={handleDashboardViewOrder}
            onViewOrders={() => {
              setSelectedOrderNumber("");
              setActiveTab("orders");
            }}
          />
        )}

        {/* Ticket records can inherit a status filter from a Dashboard KPI. */}
        {activeTab === "tickets" && (
          <TicketsTab
            token={token}
            statusFilter={ticketStatusFilter}
            onClearStatusFilter={() => setTicketStatusFilter("")}
          />
        )}
        {activeTab === "customers" && <CustomersTab token={token} />}
        {activeTab === "orders" && (
          <OrdersTab
            token={token}
            selectedOrderNumber={selectedOrderNumber}
            onViewOrder={handleDashboardViewOrder}
            onClearSelectedOrder={() => setSelectedOrderNumber("")}
          />
        )}
        {/* {activeTab === "ordersByCustomer" && (
          <OrdersByCustomerTab token={token} />
        )} */}
        {activeTab === "products" && <ProductsTab />}

        {/* Select an AI workflow, then render the matching tool panel. */}
        {activeTab === "copilot" && (
          <section className="assistant-hub">
            <div
              className="assistant-feature-grid"
              aria-label="AI Assistant features"
            >
              {ASSISTANT_FEATURES.map((feature) => (
                <button
                  key={feature.id}
                  type="button"
                  aria-pressed={assistantFeature === feature.id}
                  className={`assistant-feature-card ${
                    assistantFeature === feature.id ? "active" : ""
                  }`}
                  onClick={() => handleAssistantFeatureChange(feature.id)}
                >
                  <span className="assistant-feature-icon" aria-hidden="true">
                    <i className={`bi ${feature.icon}`}></i>
                  </span>
                  <span className="assistant-feature-copy">
                    <strong>{feature.label}</strong>
                    <small>{feature.description}</small>
                  </span>
                  <i
                    className="bi bi-chevron-right assistant-feature-arrow"
                    aria-hidden="true"
                  ></i>
                </button>
              ))}
            </div>

            {/* Ticket Summary keeps its dedicated ticket-number analysis flow. */}
            {assistantFeature === "ticket_summary" ? (
              <section className="assistant-panel">
                <div className="assistant-heading">
                  <span className="assistant-icon">
                    <i className="bi bi-ticket-detailed" aria-hidden="true"></i>
                  </span>
                  <div>
                    <p className="workspace-eyebrow">TICKET INTELLIGENCE</p>
                    <h2>Ticket Summary</h2>
                    <p>
                      Review customer context, conversation, and recommended
                      actions.
                    </p>
                  </div>
                </div>
                {assistantTickets.length > 0 && (
                  <div className="assistant-tool-field mb-3">
                    <label
                      className="form-label"
                      htmlFor="ticket-summary-select"
                    >
                      Quick-select an existing ticket
                    </label>
                    <select
                      id="ticket-summary-select"
                      className="form-select"
                      value={
                        assistantTickets.some(
                          (t) => t.ticket_number === ticketNumber,
                        )
                          ? ticketNumber
                          : ""
                      }
                      onChange={(event) => {
                        const selected = event.target.value;
                        setTicketNumber(selected);
                        setTicketSummaryError("");
                        if (selected) {
                          loadDashboard(selected);
                        }
                      }}
                    >
                      <option value="">
                        Choose from {assistantTickets.length} tickets...
                      </option>
                      {assistantTickets.map((t) => (
                        <option key={t.id} value={t.ticket_number}>
                          {t.ticket_number} — {t.subject} ({t.status})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <div className="assistant-form ticket-summary-form">
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Enter Ticket Number (e.g. TKT-001)"
                    value={ticketNumber}
                    onChange={(event) => {
                      setTicketNumber(event.target.value);
                      if (ticketSummaryError) {
                        setTicketSummaryError("");
                      }
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        loadDashboard();
                      }
                    }}
                  />
                  <button
                    className="btn btn-primary"
                    onClick={() => loadDashboard()}
                    disabled={loading}
                    type="button"
                  >
                    <i className="bi bi-stars" aria-hidden="true"></i>
                    {loading ? "Analyzing..." : "Analyze Ticket"}
                  </button>
                  <button
                    className="btn btn-outline-secondary assistant-reset-button"
                    onClick={clearTicketSummary}
                    disabled={loading}
                    type="button"
                  >
                    <i
                      className="bi bi-arrow-counterclockwise"
                      aria-hidden="true"
                    ></i>
                    Clear
                  </button>
                  <span className="ticket-summary-ai-label">
                    <i className="bi bi-stars" aria-hidden="true"></i>
                    AI summary grounded in live ticket, order, and customer data
                  </span>
                </div>
                {ticketSummaryError && (
                  <div className="alert alert-warning mt-3 mb-0" role="alert">
                    {ticketSummaryError}
                  </div>
                )}
              </section>
            ) : (
              <section
                className={`assistant-panel assistant-tool-panel ${
                  assistantFeature === "order_lookup"
                    ? "assistant-order-lookup"
                    : assistantFeature === "product_lookup"
                      ? "assistant-product-lookup"
                      : ""
                }`}
              >
                <div className="assistant-heading">
                  <span className="assistant-icon">
                    <i
                      className={`bi ${
                        ASSISTANT_FEATURES.find(
                          (feature) => feature.id === assistantFeature,
                        )?.icon
                      }`}
                      aria-hidden="true"
                    ></i>
                  </span>
                  <div>
                    <p className="workspace-eyebrow">AI SUPPORT TOOL</p>
                    <h2>
                      {
                        ASSISTANT_FEATURES.find(
                          (feature) => feature.id === assistantFeature,
                        )?.label
                      }
                    </h2>
                    <p>
                      {
                        ASSISTANT_FEATURES.find(
                          (feature) => feature.id === assistantFeature,
                        )?.description
                      }
                    </p>
                  </div>
                </div>

                {(assistantFeature === "order_lookup" ||
                  assistantFeature === "create_ticket") && (
                  <div className="assistant-tool-field">
                    <label
                      className="form-label"
                      htmlFor="assistant-customer"
                    >
                      {assistantFeature === "create_ticket"
                        ? "Create ticket for"
                        : "Customer"}
                    </label>
                    <select
                      id="assistant-customer"
                      className="form-select"
                      value={assistantCustomerId}
                      disabled={assistantCustomerLoading}
                      onChange={(event) =>
                        setAssistantCustomerId(event.target.value)
                      }
                    >
                      <option value="">
                        {assistantCustomerLoading
                          ? "Loading customers..."
                          : "Select a customer"}
                      </option>
                      {assistantCustomers.map((customer) => (
                        <option
                          key={customer.customer_id}
                          value={customer.customer_id}
                        >
                          {customer.full_name &&
                          customer.full_name.toLowerCase() !==
                            customer.username.toLowerCase()
                            ? `${customer.username} (${customer.full_name})`
                            : `${customer.username}${customer.email ? ` — ${customer.email}` : ""}`}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="assistant-tool-field">
                  <label className="form-label" htmlFor="assistant-question">
                    {assistantFeature === "product_recommendation"
                      ? "Customer requirements"
                      : assistantFeature === "create_ticket"
                        ? "Customer issue"
                      : "What would you like to know?"}
                  </label>
                  <textarea
                    id="assistant-question"
                    className="form-control assistant-question-input"
                    rows="3"
                    placeholder={
                      assistantFeature === "order_lookup"
                        ? "For example: What is the status of the latest order?"
                        : assistantFeature === "product_lookup"
                          ? "For example: Which wireless products are in stock?"
                          : assistantFeature === "create_ticket"
                            ? "Describe the customer's issue, what happened, and any troubleshooting already tried."
                            : "For example: Recommend a lightweight laptop for travel under ₹50,000."
                    }
                    value={assistantQuestion}
                    onChange={(event) =>
                      setAssistantQuestion(event.target.value)
                    }
                  />
                </div>

                <div className="assistant-tool-actions">
                  <div className="assistant-tool-buttons">
                    <button
                      className="btn btn-primary"
                      onClick={runSelectedAssistantFeature}
                      disabled={assistantLoading || assistantCustomerLoading}
                    >
                      {(assistantFeature === "order_lookup" ||
                        assistantFeature === "product_lookup" ||
                        assistantFeature === "product_recommendation" ||
                        assistantFeature === "create_ticket") &&
                      assistantLoading ? (
                        <img
                          className="assistant-button-loader"
                          src={loadingGif}
                          alt=""
                          aria-hidden="true"
                        />
                      ) : (
                        <i
                          className={`bi ${
                            assistantLoading ? "bi-hourglass-split" : "bi-stars"
                          }`}
                          aria-hidden="true"
                        ></i>
                      )}
                      {assistantLoading
                        ? assistantFeature === "order_lookup"
                          ? "Looking up..."
                            : assistantFeature === "product_lookup"
                              ? "Searching..."
                              : assistantFeature === "product_recommendation"
                                ? "Finding matches..."
                                : assistantFeature === "create_ticket"
                                  ? "Preparing draft..."
                                : "Working..."
                        : assistantFeature === "order_lookup"
                          ? "Look Up Orders"
                          : assistantFeature === "product_lookup"
                            ? "Search Products"
                            : assistantFeature === "create_ticket"
                              ? "Generate Ticket Draft"
                              : "Get Recommendations"}
                    </button>
                    {(assistantFeature === "order_lookup" ||
                      assistantFeature === "product_lookup" ||
                      assistantFeature === "product_recommendation" ||
                      assistantFeature === "create_ticket") && (
                      <button
                        className="btn btn-outline-secondary assistant-reset-button"
                        onClick={
                          assistantFeature === "order_lookup"
                            ? resetOrderLookup
                            : assistantFeature === "create_ticket"
                              ? resetTicketCreation
                              : resetProductAssistant
                        }
                        disabled={assistantLoading || assistantCustomerLoading}
                        type="button"
                      >
                        <i
                          className="bi bi-arrow-counterclockwise"
                          aria-hidden="true"
                        ></i>
                        Clear
                      </button>
                    )}
                  </div>
                  {assistantFeature === "order_lookup" && (
                    <span>
                      Order answers are generated by Ollama LLM using this
                      customer's order history.
                    </span>
                  )}
                  {assistantFeature === "product_lookup" && (
                    <span>
                      Product answers are generated by Ollama LLM using the
                      available product catalog.
                    </span>
                  )}
                  {assistantFeature === "product_recommendation" && (
                    <span>
                      Recommendations are generated by Ollama LLM using the
                      available product catalog and stated requirements.
                    </span>
                  )}
                  {assistantFeature === "create_ticket" && (
                    <span>
                      Review and edit the AI-generated details before creating
                      the ticket for the selected customer.
                    </span>
                  )}
                  {assistantFeature !== "order_lookup" &&
                    assistantFeature !== "product_lookup" && (
                      assistantFeature !== "product_recommendation" &&
                      assistantFeature !== "create_ticket" && (
                        <span>
                          Answers are based on available workspace data.
                        </span>
                      )
                    )}
                </div>

                {assistantError && (
                  <div className="alert alert-warning mt-3 mb-0" role="alert">
                    {assistantError}
                  </div>
                )}

                {/* Show a confirmation only after the create-ticket API succeeds. */}
                {ticketCreated && (
                  <div className="alert alert-success mt-3 mb-0" role="status">
                    Ticket {ticketCreated.ticket_number} was created
                    successfully for{" "}
                    {assistantCustomers.find(
                      (customer) =>
                        customer.customer_id === ticketCreated.user_id,
                    )?.username || "the selected customer"}
                    .
                  </div>
                )}

                {/* Let the executive verify and edit AI-generated ticket details. */}
                {ticketPreview && (
                  <section
                    className="assistant-answer-card ticket-draft-card"
                    aria-label="Review ticket draft"
                  >
                    <div className="assistant-answer-heading">
                      <span className="assistant-answer-icon">
                        <i
                          className="bi bi-pencil-square"
                          aria-hidden="true"
                        ></i>
                      </span>
                      <div>
                        <p className="workspace-eyebrow">
                          REVIEW BEFORE CREATING
                        </p>
                        <h3>Ticket Draft</h3>
                      </div>
                    </div>
                    <div className="assistant-tool-field ticket-draft-field">
                      <label
                        className="form-label"
                        htmlFor="ticket-draft-subject"
                      >
                        Subject
                      </label>
                      <input
                        id="ticket-draft-subject"
                        className="form-control"
                        value={ticketPreview.subject}
                        onChange={(event) =>
                          setTicketPreview((draft) => ({
                            ...draft,
                            subject: event.target.value,
                          }))
                        }
                      />
                    </div>
                    <div className="assistant-tool-field ticket-draft-field">
                      <label
                        className="form-label"
                        htmlFor="ticket-draft-description"
                      >
                        Description
                      </label>
                      <textarea
                        id="ticket-draft-description"
                        className="form-control assistant-question-input"
                        rows="4"
                        value={ticketPreview.description}
                        onChange={(event) =>
                          setTicketPreview((draft) => ({
                            ...draft,
                            description: event.target.value,
                          }))
                        }
                      />
                    </div>
                    <div className="assistant-tool-field ticket-draft-field">
                      <label
                        className="form-label"
                        htmlFor="ticket-draft-priority"
                      >
                        Priority
                      </label>
                      <select
                        id="ticket-draft-priority"
                        className="form-select"
                        value={ticketPreview.priority}
                        onChange={(event) =>
                          setTicketPreview((draft) => ({
                            ...draft,
                            priority: event.target.value,
                          }))
                        }
                      >
                        {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map(
                          (priority) => (
                            <option key={priority} value={priority}>
                              {priority}
                            </option>
                          ),
                        )}
                      </select>
                    </div>
                    <div className="assistant-tool-buttons">
                      <button
                        className="btn btn-primary"
                        onClick={submitTicket}
                        disabled={
                          ticketCreateLoading ||
                          !ticketPreview.subject.trim() ||
                          !ticketPreview.description.trim()
                        }
                        type="button"
                      >
                        <i
                          className={`bi ${ticketCreateLoading ? "bi-hourglass-split" : "bi-plus-circle"}`}
                          aria-hidden="true"
                        ></i>
                        {ticketCreateLoading
                          ? "Creating ticket..."
                          : "Create Ticket"}
                      </button>
                      <button
                        className="btn btn-outline-secondary assistant-reset-button"
                        onClick={resetTicketCreation}
                        disabled={ticketCreateLoading}
                        type="button"
                      >
                        Discard draft
                      </button>
                    </div>
                  </section>
                )}

                {assistantResponse && (
                  <div className="assistant-answer-card" aria-live="polite">
                    <div className="assistant-answer-heading">
                      <span className="assistant-answer-icon">
                        <i className="bi bi-check2-circle" aria-hidden="true"></i>
                      </span>
                      <div>
                        <p className="workspace-eyebrow">ASSISTANT RESULT</p>
                        <h3>
                          {assistantFeature === "order_lookup"
                            ? "Order Lookup"
                            : assistantFeature === "product_lookup"
                              ? "Product Details"
                              : "Recommended Products"}
                        </h3>
                      </div>
                    </div>
                    {assistantFeature === "order_lookup" ? (
                      (() => {
                        const formatted =
                          formatOrderLookupResponse(assistantResponse);

                        if (formatted.orders.length === 0) {
                          return (
                            <p className="assistant-answer-text">
                              {formatted.cleanedText}
                            </p>
                          );
                        }

                        return (
                          <div className="order-lookup-results">
                            {formatted.introduction && (
                              <p className="order-lookup-intro">
                                {formatted.introduction}
                              </p>
                            )}
                            <div className="order-lookup-list">
                              {formatted.orders.map((order, index) => (
                                <article
                                  className="order-result-card"
                                  key={`${order.orderNumber}-${index}`}
                                >
                                  <div className="order-result-heading">
                                    <span className="order-result-index">
                                      {formatted.orders.length > 1
                                        ? `Order ${index + 1}`
                                        : "Order"}
                                    </span>
                                    <strong>{order.orderNumber}</strong>
                                  </div>
                                  <dl className="order-result-details">
                                    {order.details.map((detail, detailIndex) => (
                                      <div
                                        className="order-result-detail"
                                        key={`${detail.label}-${detailIndex}`}
                                      >
                                        <dt>{detail.label}</dt>
                                        <dd>{detail.value}</dd>
                                      </div>
                                    ))}
                                  </dl>
                                </article>
                              ))}
                            </div>
                          </div>
                        );
                      })()
                    ) : (
                      assistantFeature === "product_lookup" ||
                      assistantFeature === "product_recommendation"
                    ) ? (
                      (() => {
                        const formatted =
                          formatProductLookupResponse(assistantResponse);

                        if (formatted.products.length === 0) {
                          return (
                            <p className="assistant-answer-text">
                              {formatted.cleanedText}
                            </p>
                          );
                        }

                        return (
                          <div className="product-lookup-results">
                            {formatted.introduction && (
                              <p className="product-lookup-intro">
                                {formatted.introduction}
                              </p>
                            )}
                            <div className="product-lookup-list">
                              {formatted.products.map((product, index) => (
                                <article
                                  className="product-result-card"
                                  key={`${product.name}-${index}`}
                                >
                                  <div className="product-result-heading">
                                    <span className="product-result-index">
                                      {formatted.products.length > 1
                                        ? assistantFeature ===
                                          "product_recommendation"
                                          ? `Recommendation ${index + 1}`
                                          : `Product ${index + 1}`
                                        : assistantFeature ===
                                          "product_recommendation"
                                          ? "Recommendation"
                                          : "Product"}
                                    </span>
                                    <strong>{product.name}</strong>
                                  </div>
                                  <dl className="product-result-details">
                                    {product.details.map((detail, detailIndex) => (
                                      <div
                                        className="product-result-detail"
                                        key={`${detail.label}-${detailIndex}`}
                                      >
                                        <dt>{detail.label}</dt>
                                        <dd>{detail.value}</dd>
                                      </div>
                                    ))}
                                  </dl>
                                </article>
                              ))}
                            </div>
                          </div>
                        );
                      })()
                    ) : (
                      <p className="assistant-answer-text">
                        {assistantResponse}
                      </p>
                    )}
                  </div>
                )}
              </section>
            )}
          </section>
        )}

        {/* Ticket Summary loading state while the analysis request is running. */}
        {loading && (
          <div className="ticket-summary-loading" role="status" aria-live="polite">
            <div className="ticket-summary-loading-icon" aria-hidden="true">
              <span className="ticket-summary-loading-ring"></span>
              <i className="bi bi-ticket-detailed"></i>
            </div>
            <h3>Preparing your ticket summary</h3>
            <p>
              Reviewing the ticket, customer context, and conversation history.
              This may take a moment.
            </p>
          </div>
        )}

        {/* Detailed AI insights are shown after a ticket summary is available. */}
        {activeTab === "copilot" &&
          assistantFeature === "ticket_summary" &&
          dashboard && (
          <div className="row assistant-results ticket-summary-results">
            <div className="col-lg-4">
              <TicketOverviewCard summary={dashboard.executive_summary} />
              <OrderDetailsCard order={dashboard.customer_360.latest_order} />

              <div className="card mb-3">
                <div className="card-header">Customer 360</div>
                <div className="card-body customer-metrics-grid">
                  <div className="customer-metric customer-metric-name">
                    <span className="customer-metric-label">Customer</span>
                    <strong className="customer-metric-value">
                      {dashboard.customer_360.username}
                    </strong>
                  </div>
                  <div className="customer-metric customer-metric-orders">
                    <span className="customer-metric-label">Total Orders</span>
                    <strong className="customer-metric-value">
                      {dashboard.customer_360.total_orders}
                    </strong>
                  </div>
                  <div className="customer-metric customer-metric-tickets">
                    <span className="customer-metric-label">Total Tickets</span>
                    <strong className="customer-metric-value">
                      {dashboard.customer_360.total_tickets}
                    </strong>
                  </div>
                  <div className="customer-metric customer-metric-open">
                    <span className="customer-metric-label">Open Tickets</span>
                    <strong className="customer-metric-value">
                      {dashboard.customer_360.open_tickets}
                    </strong>
                  </div>
                </div>
              </div>

              <TicketTimeline history={dashboard.ticket_summary.history} />
            </div>

            <div className="col-lg-8">
              <div className="card mb-3">
                <div className="card-header">Executive Summary</div>
                <div className="card-body">
                  <p>
                    <strong className="ticket-summary-label">Issue:</strong>{" "}
                    {dashboard.executive_summary.issue_summary}
                  </p>
                  <p>
                    <strong className="ticket-summary-label">Status:</strong>{" "}
                    {dashboard.executive_summary.current_status}
                  </p>
                  <p>
                    <strong className="ticket-summary-label">
                      Customer Concern:
                    </strong>{" "}
                    {dashboard.executive_summary.key_customer_concern}
                  </p>
                  <p>
                    <strong className="ticket-summary-label">Next Action:</strong>{" "}
                    {dashboard.executive_summary.recommended_next_action}
                  </p>
                </div>
              </div>

              <DraftResponseCard draft={dashboard.draft_response} />
              <ConversationHistoryCard
                messages={dashboard.ticket_summary.messages}
              />

              <div className="card">
                <div className="card-header">Recommended Action</div>
                <div className="card-body">
                  <h5>{dashboard.next_action.recommended_action}</h5>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="workspace-footer">
        <div className="footer-identity">
          <span className="footer-logo" aria-hidden="true">
            <i className="bi bi-headset"></i>
          </span>
          <span className="footer-brand">
            <strong>Support Desk</strong>
            <small>Customer experience operations</small>
          </span>
        </div>
        <p className="footer-tagline">
          Thoughtful service. <strong>Better outcomes.</strong>
        </p>
      </footer>
    </div>
  );
}

export default CopilotPage;
