import { Link } from "react-router-dom";
import { useCart } from "../context/cartContextObject";
import { useToast } from "../context/toastContextObject";
import {
  formatINR,
  handleProductImageError,
} from "../utils/formatters";

function ProductCard({ product }) {
  const { addItem } = useCart();
  const { showToast } = useToast();

  const handleQuickAdd = () => {
    const result = addItem(product, 1, true);
    if (!result.added) {
      showToast(`'${product.name}' is out of stock.`, "warning");
    } else if (result.capped) {
      showToast(
        `Maximum available stock (${product.stock}) reached for '${product.name}'.`,
        "warning",
      );
    } else {
      showToast(`Added '${product.name}' to your cart.`, "success");
    }
  };

  return (
    <article className="sg-product-card">
      <Link to={`/product/${product.id}`} className="sg-product-media">
        <img
          src={product.image_url}
          alt={product.name}
          loading="lazy"
          onError={handleProductImageError}
        />
        {product.is_out_of_stock ? (
          <span className="sg-stock-pill sg-stock-out">Out of Stock</span>
        ) : product.is_low_stock ? (
          <span className="sg-stock-pill sg-stock-low">
            Only {product.stock} left
          </span>
        ) : (
          <span className="sg-stock-pill sg-stock-in">In Stock</span>
        )}
      </Link>

      <div className="sg-product-body">
        <div className="sg-product-meta">
          <span>{product.category}</span>
          <span className="sg-product-brand">{product.brand}</span>
        </div>

        <Link to={`/product/${product.id}`} className="sg-product-title">
          {product.name}
        </Link>

        <p className="sg-product-desc">
          {product.description || "Engineered for dependable everyday performance."}
        </p>

        <div className="sg-product-footer">
          <div className="sg-product-price">
            {formatINR(product.price)}
            <small>Incl. all taxes</small>
          </div>

          <button
            type="button"
            className="sg-add-btn"
            disabled={product.is_out_of_stock}
            onClick={handleQuickAdd}
          >
            <i
              className={`bi ${
                product.is_out_of_stock ? "bi-slash-circle" : "bi-bag-plus"
              }`}
              aria-hidden="true"
            ></i>
            {product.is_out_of_stock ? "Sold Out" : "Add"}
          </button>
        </div>
      </div>
    </article>
  );
}

export default ProductCard;
