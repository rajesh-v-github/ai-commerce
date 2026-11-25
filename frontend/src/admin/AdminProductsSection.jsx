import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useToast } from "../context/toastContextObject";
import {
  createAdminProduct,
  deleteAdminProduct,
  fetchAdminProducts,
  generateAiProductDescription,
  updateAdminProduct,
  uploadAdminProductImage,
} from "../services/adminService";
import {
  FALLBACK_PRODUCT_IMAGE,
  formatINR,
  handleProductImageError,
} from "../utils/formatters";

const CATEGORY_SKU_CODES = {
  audio: "AUD",
  "gaming accessories": "GAM",
  "laptop bags & cases": "BAG",
  "computer accessories": "ACC",
  "webcams & video conferencing": "WEB",
  webcams: "WEB",
  "keyboards & mice": "KBM",
  laptops: "LAP",
  wearables: "WRB",
  "power & charging": "PWR",
  "monitors & displays": "MON",
};

function deriveSkuCategoryCode(category, name) {
  const normalizedCategory = (category || "").trim().toLowerCase();
  if (CATEGORY_SKU_CODES[normalizedCategory]) {
    return CATEGORY_SKU_CODES[normalizedCategory];
  }

  const combined = `${category || ""} ${name || ""}`.toLowerCase();
  const keywordMap = [
    [["earbud", "speaker", "headset", "headphone", "audio"], "AUD"],
    [["gaming"], "GAM"],
    [["backpack", "bag", "case", "sleeve"], "BAG"],
    [["webcam", "camera", "conferencing"], "WEB"],
    [["keyboard", "mouse", "mice"], "KBM"],
    [["laptop", "notebook"], "LAP"],
    [["watch", "wearable", "band"], "WRB"],
    [["power", "charger", "charging", "battery"], "PWR"],
    [["monitor", "display"], "MON"],
    [["hub", "dock", "adapter", "cable", "accessory", "accessories"], "ACC"],
  ];
  for (const [keywords, code] of keywordMap) {
    if (keywords.some((kw) => combined.includes(kw))) {
      return code;
    }
  }

  const source = (category || "").trim() || (name || "").trim();
  const alpha = source.toUpperCase().replace(/[^A-Z0-9]+/g, "");
  if (alpha.length >= 3) {
    return alpha.slice(0, 3);
  }
  if (alpha.length > 0) {
    return alpha.padEnd(3, "X");
  }
  return "PRD";
}

function formatAutoSku(category, name, serialNumber) {
  const code = deriveSkuCategoryCode(category, name);
  const serial = String(Math.max(1, Number(serialNumber) || 1)).padStart(
    3,
    "0",
  );
  return `SG-${code}-${serial}`;
}

function extractSkuSerial(sku, fallbackId) {
  if (sku) {
    const match = String(sku)
      .trim()
      .match(/(\d+)$/);
    if (match) {
      return Number(match[1]);
    }
  }
  return Number(fallbackId) || 1;
}

const EMPTY_FORM = {
  name: "",
  sku: "",
  category: "",
  price: "",
  stock: "15",
  low_stock_threshold: "5",
  image_url: "",
  description: "",
  is_active: true,
  key_features: "",
  tone: "balanced",
};

function AdminProductsSection() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { showToast } = useToast();

  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [nextSkuSerial, setNextSkuSerial] = useState(16);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [categoryFilter, setCategoryFilter] = useState(
    searchParams.get("category") || "",
  );
  const [stockStatus, setStockStatus] = useState(
    searchParams.get("stock_status") || "",
  );
  const [sortBy, setSortBy] = useState("newest");

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [originalDescription, setOriginalDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [generatingAi, setGeneratingAi] = useState(false);
  const [aiMeta, setAiMeta] = useState(null);
  const [aiError, setAiError] = useState("");
  const [modalError, setModalError] = useState("");

  const loadProducts = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchAdminProducts({
        search: search.trim() || undefined,
        category: categoryFilter || undefined,
        stock_status: stockStatus || undefined,
        sort_by: sortBy,
      });
      setProducts(data.products || data.items || []);
      setCategories(data.categories || []);
      if (data.next_sku_serial) {
        setNextSkuSerial(Number(data.next_sku_serial));
      }
    } catch (err) {
      console.error(err);
      showToast("Failed to load product catalog.", "danger");
    } finally {
      setLoading(false);
    }
  }, [search, categoryFilter, stockStatus, sortBy, showToast]);

  const editIdParam = searchParams.get("edit") || "";

  useEffect(() => {
    let active = true;
    const fetchProducts = async () => {
      try {
        const data = await fetchAdminProducts({
          search: search.trim() || undefined,
          category: categoryFilter || undefined,
          stock_status: stockStatus || undefined,
          sort_by: sortBy,
        });
        const loadedProducts = data.products || data.items || [];
        let targetEditProduct = null;
        if (editIdParam) {
          targetEditProduct =
            loadedProducts.find(
              (p) => Number(p.id) === Number(editIdParam),
            ) || null;
          if (!targetEditProduct) {
            const unfiltered = await fetchAdminProducts({});
            const allList = unfiltered.products || unfiltered.items || [];
            targetEditProduct =
              allList.find((p) => Number(p.id) === Number(editIdParam)) ||
              null;
          }
        }
        if (active) {
          setProducts(loadedProducts);
          setCategories(data.categories || []);
          if (data.next_sku_serial) {
            setNextSkuSerial(Number(data.next_sku_serial));
          }
          if (targetEditProduct) {
            setEditingProduct(targetEditProduct);
            setForm({
              name: targetEditProduct.name || "",
              sku: targetEditProduct.sku || "",
              category: targetEditProduct.category || "",
              price: String(targetEditProduct.price ?? ""),
              stock: String(targetEditProduct.stock ?? 0),
              low_stock_threshold: String(
                targetEditProduct.low_stock_threshold ?? 5,
              ),
              image_url: targetEditProduct.image_url || "",
              description: targetEditProduct.description || "",
              is_active: targetEditProduct.is_active !== false,
              key_features: "",
              tone: "balanced",
            });
            setOriginalDescription(targetEditProduct.description || "");
            setAiMeta(null);
            setAiError("");
            setModalError("");
            setModalOpen(true);
            const cleanedParams = new URLSearchParams(searchParams);
            cleanedParams.delete("edit");
            setSearchParams(cleanedParams, { replace: true });
          }
        }
      } catch (err) {
        console.error(err);
        if (active) {
          showToast("Failed to load product catalog.", "danger");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    fetchProducts();
    return () => {
      active = false;
    };
  }, [
    search,
    categoryFilter,
    stockStatus,
    sortBy,
    editIdParam,
    searchParams,
    setSearchParams,
    showToast,
  ]);

  const openCreateModal = () => {
    setEditingProduct(null);
    setForm({
      ...EMPTY_FORM,
      category: categories[0] || "Computer Accessories",
    });
    setOriginalDescription("");
    setAiMeta(null);
    setAiError("");
    setModalError("");
    setModalOpen(true);
  };

  const openEditModal = (prod) => {
    setEditingProduct(prod);
    setForm({
      name: prod.name || "",
      sku: prod.sku || "",
      category: prod.category || "",
      price: String(prod.price ?? ""),
      stock: String(prod.stock ?? 0),
      low_stock_threshold: String(prod.low_stock_threshold ?? 5),
      image_url: prod.image_url || "",
      description: prod.description || "",
      is_active: prod.is_active !== false,
      key_features: "",
      tone: "balanced",
    });
    setOriginalDescription(prod.description || "");
    setAiMeta(null);
    setAiError("");
    setModalError("");
    setModalOpen(true);
  };

  const handleImageFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    try {
      setUploadingImage(true);
      const uploaded = await uploadAdminProductImage(file);
      setForm((prev) => ({ ...prev, image_url: uploaded.image_url }));
      showToast("Product image uploaded successfully.", "success");
    } catch (err) {
      const detail = err.response?.data?.detail;
      showToast(
        typeof detail === "string" ? detail : "Image upload failed.",
        "danger",
      );
    } finally {
      setUploadingImage(false);
      event.target.value = "";
    }
  };

  const handleGenerateAiDescription = async () => {
    setAiError("");
    if (!form.name.trim()) {
      setAiError("Enter a Product Name first so AI can tailor the description.");
      return;
    }
    try {
      setGeneratingAi(true);
      const seedAttributes =
        originalDescription && originalDescription.trim().length <= 140
          ? originalDescription.trim()
          : form.description.trim().length <= 140
            ? form.description.trim()
            : undefined;
      const result = await generateAiProductDescription({
        name: form.name.trim(),
        category: form.category.trim() || "Electronics",
        brand: editingProduct?.brand || undefined,
        specifications: editingProduct?.specifications || undefined,
        target_audience: editingProduct?.target_audience || undefined,
        features: form.key_features.trim() || undefined,
        attributes: seedAttributes,
        tone: form.tone,
      });
      setForm((prev) => ({ ...prev, description: result.description }));
      setAiMeta({
        provider: result.provider,
        model: result.model,
      });
      const providerLabel =
        result.provider === "ollama"
          ? `Ollama (${result.model})`
          : "SoranoGear AI Copywriter";
      showToast(
        `AI draft generated via ${providerLabel}. Review and click Save Product Changes to persist.`,
        "info",
      );
    } catch (err) {
      const detail = err.response?.data?.detail;
      setAiError(
        typeof detail === "string"
          ? detail
          : "AI description service is currently unreachable. Ensure Ollama is running or edit manually.",
      );
    } finally {
      setGeneratingAi(false);
    }
  };

  const handleSaveProduct = async (e) => {
    e.preventDefault();
    setModalError("");

    const numericPrice = Number(form.price);
    const numericStock = Number(form.stock);
    const numericThreshold = Number(form.low_stock_threshold);

    if (!form.name.trim() || !form.category.trim()) {
      setModalError("Product name and category are required.");
      return;
    }
    if (Number.isNaN(numericPrice) || numericPrice <= 0) {
      setModalError("Price must be greater than ₹0.");
      return;
    }
    if (Number.isNaN(numericStock) || numericStock < 0) {
      setModalError("Stock quantity must be 0 or higher.");
      return;
    }

    const computedAutoSku = editingProduct
      ? formatAutoSku(
          form.category,
          form.name,
          extractSkuSerial(editingProduct.sku, editingProduct.id),
        )
      : formatAutoSku(form.category, form.name, nextSkuSerial);

    const payload = {
      name: form.name.trim(),
      sku: editingProduct ? computedAutoSku : null,
      category: form.category.trim(),
      price: numericPrice,
      stock: Math.floor(numericStock),
      low_stock_threshold: Math.max(0, Math.floor(numericThreshold || 5)),
      image_url: form.image_url.trim() || null,
      description: form.description.trim(),
      is_active: Boolean(form.is_active),
    };

    try {
      setSaving(true);
      if (editingProduct) {
        await updateAdminProduct(editingProduct.id, payload);
        showToast(`Updated "${payload.name}".`, "success");
      } else {
        await createAdminProduct(payload);
        showToast(`Created product "${payload.name}".`, "success");
      }
      setModalOpen(false);
      await loadProducts();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setModalError(
        typeof detail === "string"
          ? detail
          : "Unable to save product. Check SKU uniqueness and fields.",
      );
    } finally {
      setSaving(false);
    }
  };

  const handleQuickStockAdjust = async (prod, delta) => {
    const nextStock = Math.max(0, (prod.stock || 0) + delta);
    if (nextStock === prod.stock) {
      return;
    }
    try {
      await updateAdminProduct(prod.id, { stock: nextStock });
      setProducts((prev) =>
        prev.map((p) =>
          p.id === prod.id
            ? {
                ...p,
                stock: nextStock,
                in_stock: Boolean(p.is_active && nextStock > 0),
                is_low_stock: Boolean(
                  nextStock > 0 && nextStock <= p.low_stock_threshold,
                ),
              }
            : p,
        ),
      );
      showToast(`${prod.name} stock updated to ${nextStock}.`, "success");
    } catch {
      showToast("Failed to adjust stock.", "danger");
    }
  };

  const handleToggleActive = async (prod) => {
    try {
      const nextActive = !prod.is_active;
      await updateAdminProduct(prod.id, { is_active: nextActive });
      showToast(
        `${prod.name} ${nextActive ? "activated" : "deactivated"}.`,
        "info",
      );
      await loadProducts();
    } catch {
      showToast("Unable to update product status.", "danger");
    }
  };

  const handleDeleteOrDeactivate = async (prod) => {
    const confirmed = window.confirm(
      `Remove "${prod.name}"? Products with historical orders are safely deactivated to preserve order integrity; unused products are permanently deleted.`,
    );
    if (!confirmed) {
      return;
    }
    try {
      const result = await deleteAdminProduct(prod.id, false);
      showToast(result.message || "Product updated.", "info");
      await loadProducts();
    } catch (err) {
      const detail = err.response?.data?.detail;
      showToast(
        typeof detail === "string" ? detail : "Unable to remove product.",
        "danger",
      );
    }
  };

  return (
    <div className="d-grid gap-4">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
        <div>
          <h1 className="fs-3 fw-bold mb-1">
            Product &amp; Inventory Management
          </h1>
          <p className="text-muted small mb-0">
            Manage catalog listings, pricing, stock levels, product imagery, and
            AI-assisted product copywriting
          </p>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          onClick={openCreateModal}
        >
          <i className="bi bi-plus-lg me-1"></i>
          Add New Product
        </button>
      </div>

      {/* Filters Bar */}
      <div className="adm-card">
        <div className="row g-2 align-items-center">
          <div className="col-md-4">
            <div className="input-group input-group-sm">
              <span className="input-group-text bg-white">
                <i className="bi bi-search"></i>
              </span>
              <input
                type="search"
                className="form-control"
                placeholder="Search name, SKU, category, description..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          <div className="col-md-3">
            <select
              className="form-select form-select-sm"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          <div className="col-md-3">
            <select
              className="form-select form-select-sm"
              value={stockStatus}
              onChange={(e) => {
                setStockStatus(e.target.value);
                setSearchParams((prev) => {
                  const next = new URLSearchParams(prev);
                  if (e.target.value) {
                    next.set("stock_status", e.target.value);
                  } else {
                    next.delete("stock_status");
                  }
                  return next;
                });
              }}
            >
              <option value="">All Inventory States</option>
              <option value="in_stock">In Stock</option>
              <option value="low_stock">Low Stock Warning</option>
              <option value="out_of_stock">Out of Stock (0)</option>
              <option value="inactive">Inactive / Hidden</option>
            </select>
          </div>

          <div className="col-md-2">
            <select
              className="form-select form-select-sm"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="newest">Newest</option>
              <option value="name_asc">Name (A–Z)</option>
              <option value="price_asc">Price: Low → High</option>
              <option value="price_desc">Price: High → Low</option>
              <option value="stock_asc">Stock: Lowest First</option>
              <option value="stock_desc">Stock: Highest First</option>
            </select>
          </div>
        </div>
      </div>

      {/* Product Table */}
      <div className="adm-card p-0 overflow-hidden">
        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border text-primary" role="status"></div>
          </div>
        ) : products.length === 0 ? (
          <div className="text-center py-5">
            <p className="text-muted mb-2">
              No products match your current filter criteria.
            </p>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={() => {
                setSearch("");
                setCategoryFilter("");
                setStockStatus("");
                setSearchParams({});
              }}
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table adm-table table-hover mb-0">
              <thead>
                <tr>
                  <th className="ps-4">Product</th>
                  <th>SKU</th>
                  <th>Category</th>
                  <th className="text-end">Price</th>
                  <th className="text-center">Stock Level</th>
                  <th>Status</th>
                  <th className="text-end pe-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map((prod) => (
                  <tr key={prod.id}>
                    <td className="ps-4">
                      <div className="d-flex align-items-center gap-3">
                        <img
                          src={prod.image_url || FALLBACK_PRODUCT_IMAGE}
                          alt={prod.name}
                          onError={handleProductImageError}
                          style={{
                            width: "56px",
                            height: "40px",
                            objectFit: "cover",
                            borderRadius: "8px",
                            border: "1px solid #e2e8f0",
                          }}
                        />
                        <div style={{ maxWidth: "280px" }}>
                          <div className="fw-bold text-truncate">
                            {prod.name}
                          </div>
                          <div className="text-muted small text-truncate">
                            {prod.description || "No description"}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="font-monospace small text-muted">
                      {prod.sku || `SG-${prod.id}`}
                    </td>
                    <td>
                      <span className="badge bg-light text-dark border">
                        {prod.category}
                      </span>
                    </td>
                    <td className="text-end fw-bold">
                      {formatINR(prod.price)}
                    </td>
                    <td className="text-center">
                      <div className="d-inline-flex align-items-center gap-1">
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary py-0 px-2"
                          onClick={() => handleQuickStockAdjust(prod, -1)}
                          disabled={prod.stock <= 0}
                          title="Decrement stock by 1"
                        >
                          −
                        </button>
                        <span
                          className="fw-bold px-2"
                          style={{ minWidth: "36px" }}
                        >
                          {prod.stock}
                        </span>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary py-0 px-2"
                          onClick={() => handleQuickStockAdjust(prod, 1)}
                          title="Increment stock by 1"
                        >
                          +
                        </button>
                      </div>
                      <div className="text-muted" style={{ fontSize: "11px" }}>
                        Alert ≤ {prod.low_stock_threshold}
                      </div>
                    </td>
                    <td>
                      {!prod.is_active ? (
                        <span className="badge bg-secondary-subtle text-secondary">
                          Inactive
                        </span>
                      ) : prod.stock === 0 ? (
                        <span className="badge bg-danger-subtle text-danger">
                          Out of Stock
                        </span>
                      ) : prod.is_low_stock ? (
                        <span className="badge bg-warning-subtle text-warning-emphasis">
                          Low Stock
                        </span>
                      ) : (
                        <span className="badge bg-success-subtle text-success">
                          Active
                        </span>
                      )}
                    </td>
                    <td className="text-end pe-4">
                      <div className="btn-group btn-group-sm">
                        <button
                          type="button"
                          className="btn btn-outline-primary"
                          onClick={() => openEditModal(prod)}
                        >
                          <i className="bi bi-pencil-square me-1"></i>
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-secondary"
                          onClick={() => handleToggleActive(prod)}
                          title={
                            prod.is_active
                              ? "Hide from storefront"
                              : "Publish to storefront"
                          }
                        >
                          {prod.is_active ? "Hide" : "Activate"}
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-danger"
                          onClick={() => handleDeleteOrDeactivate(prod)}
                          title="Delete or Deactivate"
                        >
                          <i className="bi bi-trash"></i>
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

      {/* Add / Edit Product Modal */}
      {modalOpen && (
        <div className="adm-modal-backdrop" role="dialog" aria-modal="true">
          <form className="adm-modal-dialog" onSubmit={handleSaveProduct}>
            <div className="adm-modal-header">
              <div>
                <h2 className="fs-5 fw-bold mb-0">
                  {editingProduct
                    ? `Edit Product: ${editingProduct.name}`
                    : "Add New Catalog Product"}
                </h2>
                <p className="text-muted small mb-0">
                  Changes take effect immediately across Storefront &amp; Support
                  Copilot upon saving
                </p>
              </div>
              <button
                type="button"
                className="btn-close"
                aria-label="Close"
                onClick={() => setModalOpen(false)}
              />
            </div>

            <div className="adm-modal-body d-grid gap-3">
              {modalError && (
                <div className="alert alert-danger py-2 small mb-0">
                  {modalError}
                </div>
              )}

              <div className="row g-3">
                <div className="col-md-6">
                  <label className="form-label small fw-semibold">
                    Product Name *
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    value={form.name}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, name: e.target.value }))
                    }
                    placeholder="e.g. Studio ANC Wireless Headphones"
                  />
                </div>

                <div className="col-md-3">
                  <label className="form-label small fw-semibold d-flex align-items-center justify-content-between">
                    <span>SKU</span>
                    <span
                      className="badge bg-secondary-subtle text-secondary fw-normal"
                      style={{ fontSize: "10.5px" }}
                    >
                      <i className="bi bi-lock-fill me-1"></i>
                      Auto
                    </span>
                  </label>
                  <input
                    type="text"
                    className="form-control font-monospace bg-light text-secondary"
                    readOnly
                    tabIndex={-1}
                    aria-readonly="true"
                    value={
                      editingProduct
                        ? formatAutoSku(
                            form.category,
                            form.name,
                            extractSkuSerial(
                              editingProduct.sku,
                              editingProduct.id,
                            ),
                          )
                        : formatAutoSku(form.category, form.name, nextSkuSerial)
                    }
                    title="Auto-generated serial SKU based on category/product name and last product serial number"
                  />
                </div>

                <div className="col-md-3">
                  <label className="form-label small fw-semibold">
                    Category *
                  </label>
                  <input
                    type="text"
                    list="adm-category-datalist"
                    className="form-control"
                    required
                    value={form.category}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, category: e.target.value }))
                    }
                    placeholder="Audio"
                  />
                  <datalist id="adm-category-datalist">
                    {categories.map((cat) => (
                      <option key={cat} value={cat} />
                    ))}
                  </datalist>
                </div>

                <div className="col-md-4">
                  <label className="form-label small fw-semibold">
                    Price (INR ₹) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="1"
                    className="form-control"
                    required
                    value={form.price}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, price: e.target.value }))
                    }
                  />
                </div>

                <div className="col-md-4">
                  <label className="form-label small fw-semibold">
                    Stock Quantity *
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    className="form-control"
                    required
                    value={form.stock}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, stock: e.target.value }))
                    }
                  />
                </div>

                <div className="col-md-4">
                  <label className="form-label small fw-semibold">
                    Low-Stock Alert Threshold
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    className="form-control"
                    value={form.low_stock_threshold}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        low_stock_threshold: e.target.value,
                      }))
                    }
                  />
                </div>
              </div>

              {/* Product Image Upload + URL */}
              <div className="border rounded-3 p-3 bg-light">
                <label className="form-label small fw-semibold mb-2">
                  Product Image (Upload File or Image URL)
                </label>
                <div className="d-flex flex-wrap align-items-center gap-3">
                  <img
                    src={form.image_url || FALLBACK_PRODUCT_IMAGE}
                    alt="Preview"
                    onError={handleProductImageError}
                    style={{
                      width: "96px",
                      height: "64px",
                      objectFit: "cover",
                      borderRadius: "8px",
                      border: "1px solid #cbd5e1",
                      background: "#fff",
                    }}
                  />
                  <div className="flex-grow-1 d-grid gap-2">
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      placeholder="/product-images/wireless-earbuds.jpg or https://..."
                      value={form.image_url}
                      onChange={(e) =>
                        setForm((prev) => ({
                          ...prev,
                          image_url: e.target.value,
                        }))
                      }
                    />
                    <div className="d-flex align-items-center gap-2">
                      <label className="btn btn-sm btn-outline-secondary mb-0">
                        <i className="bi bi-upload me-1"></i>
                        {uploadingImage ? "Uploading..." : "Upload Image File"}
                        <input
                          type="file"
                          accept="image/png,image/jpeg,image/webp,image/svg+xml"
                          hidden
                          disabled={uploadingImage}
                          onChange={handleImageFileUpload}
                        />
                      </label>
                      <span className="text-muted" style={{ fontSize: "12px" }}>
                        Supports JPG, PNG, WebP, SVG (max 5 MB)
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* AI-Assisted Description Generator */}
              <div className="adm-ai-box">
                <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
                  <div>
                    <span className="fw-bold small text-primary">
                      <i className="bi bi-stars me-1"></i>
                      AI Product Copywriter
                    </span>
                    <span className="text-muted small ms-2">
                      Generates grounded storefront copy from the metadata above
                    </span>
                  </div>

                  <div className="d-flex align-items-center gap-2">
                    <select
                      className="form-select form-select-sm"
                      style={{ width: "auto" }}
                      value={form.tone}
                      onChange={(e) =>
                        setForm((prev) => ({ ...prev, tone: e.target.value }))
                      }
                    >
                      <option value="balanced">Balanced Tone</option>
                      <option value="concise">Concise</option>
                      <option value="premium">Premium</option>
                      <option value="technical">Technical</option>
                    </select>

                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      disabled={generatingAi}
                      onClick={handleGenerateAiDescription}
                    >
                      {generatingAi ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-1"></span>
                          Generating...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-magic me-1"></i>
                          {aiMeta
                            ? "Regenerate with AI"
                            : "Generate Description with AI"}
                        </>
                      )}
                    </button>
                  </div>
                </div>

                <input
                  type="text"
                  className="form-control form-control-sm bg-white"
                  placeholder="Optional key attributes / specs to include (e.g., USB-C PD 100W, aluminum chassis, hot-swappable switches)"
                  value={form.key_features}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      key_features: e.target.value,
                    }))
                  }
                />

                {aiMeta && (
                  <div className="d-flex justify-content-between align-items-center mt-2 small text-primary">
                    <span>
                      <i className="bi bi-check2-circle me-1"></i>
                      Draft generated via <strong>{aiMeta.provider}</strong> (
                      <code>{aiMeta.model}</code>). Edit freely below — saved
                      only when you submit.
                    </span>
                    {originalDescription && (
                      <button
                        type="button"
                        className="btn btn-link btn-sm p-0 text-decoration-none"
                        onClick={() =>
                          setForm((prev) => ({
                            ...prev,
                            description: originalDescription,
                          }))
                        }
                      >
                        Restore Original
                      </button>
                    )}
                  </div>
                )}

                {aiError && (
                  <div className="alert alert-warning py-2 px-3 small mt-2 mb-0">
                    <i className="bi bi-exclamation-circle me-1"></i>
                    {aiError}
                  </div>
                )}
              </div>

              {/* Editable Description Field */}
              <div>
                <label className="form-label small fw-semibold">
                  Product Description (Editable)
                </label>
                <textarea
                  rows="4"
                  className="form-control"
                  value={form.description}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      description: e.target.value,
                    }))
                  }
                  placeholder="Write or generate a customer-ready product description..."
                />
              </div>

              <div className="form-check">
                <input
                  id="prod-active-toggle"
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
                  htmlFor="prod-active-toggle"
                >
                  Published &amp; visible on customer storefront
                </label>
              </div>
            </div>

            <div className="adm-modal-footer">
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={() => setModalOpen(false)}
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
                  : editingProduct
                    ? "Save Product Changes"
                    : "Create Product"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default AdminProductsSection;
