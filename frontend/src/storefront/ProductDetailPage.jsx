import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useCart } from "../context/cartContextObject";
import { useToast } from "../context/toastContextObject";
import { getStoreProductDetail } from "../services/storeService";
import { formatINR, handleProductImageError } from "../utils/formatters";
import ProductCard from "./ProductCard";

function ProductDetailPage() {
  const { productId } = useParams();
  const navigate = useNavigate();
  const { addItem } = useCart();
  const { showToast } = useToast();

  const [product, setProduct] = useState(null);
  const [related, setRelated] = useState([]);
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const fetchDetail = async () => {
      try {
        setLoading(true);
        setError("");
        setQuantity(1);
        const data = await getStoreProductDetail(productId);
        if (active) {
          setProduct(data.product);
          setRelated(data.related_products || []);
        }
      } catch (err) {
        console.error(err);
        if (active) {
          setError(
            err.response?.status === 404
              ? "This product could not be found or is no longer active."
              : "Unable to load product details.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    fetchDetail();
    return () => {
      active = false;
    };
  }, [productId]);

  if (loading) {
    return (
      <div className="sg-container py-5 text-center">
        <div className="spinner-border text-primary" role="status"></div>
        <p className="text-muted mt-2">Loading product specifications...</p>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="sg-container py-5">
        <div className="sg-panel text-center py-5">
          <i
            className="bi bi-exclamation-circle text-warning"
            style={{ fontSize: "40px" }}
          ></i>
          <h2 className="fs-4 fw-bold mt-3">{error || "Product unavailable"}</h2>
          <Link to="/" className="sg-btn-primary mt-3">
            Back to Storefront
          </Link>
        </div>
      </div>
    );
  }

  const parsedSpecs = (product.specifications || "")
    .split("|")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((entry) => {
      const idx = entry.indexOf(":");
      if (idx > 0) {
        return {
          label: entry.slice(0, idx).trim(),
          value: entry.slice(idx + 1).trim(),
        };
      }
      return { label: "Highlight", value: entry };
    });

  const handleAddToCart = (goToCheckout = false) => {
    const res = addItem(product, quantity, !goToCheckout);
    if (!res.added) {
      showToast("This item is currently out of stock.", "warning");
      return;
    }
    if (goToCheckout) {
      navigate("/checkout");
    } else {
      showToast(`Added ${quantity} × '${product.name}' to cart.`, "success");
    }
  };

  return (
    <div className="sg-container py-4">
      <nav aria-label="breadcrumb" className="mb-3">
        <ol className="breadcrumb small mb-0">
          <li className="breadcrumb-item">
            <Link to="/" className="text-decoration-none">
              SoranoGear
            </Link>
          </li>
          <li className="breadcrumb-item">
            <Link
              to={`/?category=${encodeURIComponent(product.category)}`}
              className="text-decoration-none"
            >
              {product.category}
            </Link>
          </li>
          <li className="breadcrumb-item active" aria-current="page">
            {product.name}
          </li>
        </ol>
      </nav>

      <div className="sg-detail-grid">
        <div className="sg-detail-image-card">
          <img
            src={product.image_url}
            alt={product.name}
            onError={handleProductImageError}
          />
        </div>

        <div className="sg-detail-info">
          <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
            <span className="badge text-bg-primary bg-opacity-10 text-primary border border-primary-subtle px-3 py-2">
              {product.category}
            </span>
            {product.sku && (
              <span className="text-muted small font-monospace">
                SKU: {product.sku}
              </span>
            )}
          </div>

          <p className="text-uppercase small fw-bold text-secondary mb-1">
            {product.brand}
          </p>
          <h1 className="fs-2 fw-bold mb-3">{product.name}</h1>

          <div className="d-flex align-items-baseline gap-3 mb-3">
            <span className="fs-2 fw-extrabold" style={{ fontWeight: 800 }}>
              {formatINR(product.price)}
            </span>
            <span className="text-muted small">
              Inclusive of 18% GST •{" "}
              {product.price >= 1999
                ? "Eligible for Free Delivery"
                : "Standard Delivery ₹99"}
            </span>
          </div>

          {/* Stock Status Indicator */}
          <div className="mb-3">
            {product.is_out_of_stock ? (
              <span className="badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-2">
                <i className="bi bi-x-circle-fill me-1"></i>
                Currently Out of Stock
              </span>
            ) : product.is_low_stock ? (
              <span className="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle px-3 py-2">
                <i className="bi bi-exclamation-triangle-fill me-1"></i>
                Low Stock — Only {product.stock} left in warehouse
              </span>
            ) : (
              <span className="badge bg-success-subtle text-success border border-success-subtle px-3 py-2">
                <i className="bi bi-check-circle-fill me-1"></i>
                In Stock ({product.stock} units available)
              </span>
            )}
          </div>

          <p className="text-secondary mb-3" style={{ lineHeight: 1.7 }}>
            {product.description ||
              "Precision-crafted technology backed by SoranoTech customer support."}
          </p>

          {(parsedSpecs.length > 0 || product.target_audience) && (
            <div className="sg-spec-list">
              {parsedSpecs.map((spec, idx) => (
                <div key={idx} className="sg-spec-row">
                  <span className="text-muted fw-semibold">{spec.label}</span>
                  <span className="fw-semibold text-end">{spec.value}</span>
                </div>
              ))}
              {product.target_audience && (
                <div className="sg-spec-row">
                  <span className="text-muted fw-semibold">Designed For</span>
                  <span className="fw-semibold text-end">
                    {product.target_audience}
                  </span>
                </div>
              )}
            </div>
          )}

          {!product.is_out_of_stock && (
            <div className="d-flex flex-wrap align-items-center gap-3 mt-4">
              <div className="sg-qty-stepper" aria-label="Select quantity">
                <button
                  type="button"
                  disabled={quantity <= 1}
                  onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                >
                  −
                </button>
                <span>{quantity}</span>
                <button
                  type="button"
                  disabled={quantity >= product.stock}
                  onClick={() =>
                    setQuantity((q) => Math.min(product.stock, q + 1))
                  }
                >
                  +
                </button>
              </div>

              <button
                type="button"
                className="sg-btn-primary"
                style={{ flex: 1, minWidth: "170px" }}
                onClick={() => handleAddToCart(false)}
              >
                <i className="bi bi-bag-plus"></i>
                Add to Cart
              </button>

              <button
                type="button"
                className="btn btn-dark fw-bold px-4"
                style={{ height: "46px", borderRadius: "12px" }}
                onClick={() => handleAddToCart(true)}
              >
                Buy Now
              </button>
            </div>
          )}
        </div>
      </div>

      {related.length > 0 && (
        <section className="mt-5">
          <div className="sg-section-header">
            <div>
              <h2>You Might Also Like</h2>
              <p>Complementary gear from our catalog</p>
            </div>
          </div>
          <div className="sg-product-grid">
            {related.map((item) => (
              <ProductCard key={item.id} product={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default ProductDetailPage;
