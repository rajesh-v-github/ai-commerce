import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  getStoreCategories,
  getStoreProducts,
} from "../services/storeService";
import { formatINR, handleProductImageError } from "../utils/formatters";
import ProductCard from "./ProductCard";

function StoreHomePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const catalogRef = useRef(null);

  const selectedCategory = searchParams.get("category") || "";
  const urlQuery = searchParams.get("q") || "";

  const [searchInput, setSearchInput] = useState(urlQuery);
  const [brandFilter, setBrandFilter] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [inStockOnly, setInStockOnly] = useState(false);
  const [sortBy, setSortBy] = useState("featured");

  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [availableBrands, setAvailableBrands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [prevUrlQuery, setPrevUrlQuery] = useState(urlQuery);
  if (urlQuery !== prevUrlQuery) {
    setPrevUrlQuery(urlQuery);
    setSearchInput(urlQuery);
  }

  useEffect(() => {
    let active = true;
    getStoreCategories()
      .then((data) => {
        if (active) {
          setCategories(data);
        }
      })
      .catch((err) => console.error(err));
    return () => {
      active = false;
    };
  }, []);

  const buildProductParams = useCallback(() => {
    const params = {
      sort: sortBy,
      in_stock: inStockOnly,
    };
    if (urlQuery.trim()) {
      params.q = urlQuery.trim();
    }
    if (selectedCategory) {
      params.category = selectedCategory;
    }
    if (brandFilter) {
      params.brand = brandFilter;
    }
    if (maxPrice !== "" && !Number.isNaN(Number(maxPrice))) {
      params.max_price = Number(maxPrice);
    }
    return params;
  }, [urlQuery, selectedCategory, brandFilter, maxPrice, inStockOnly, sortBy]);

  const loadProducts = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getStoreProducts(buildProductParams());
      setProducts(data.products || []);
      setAvailableBrands(data.brands || []);
    } catch (err) {
      console.error(err);
      setError("Unable to load the product catalog. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [buildProductParams]);

  useEffect(() => {
    let active = true;
    const fetchCatalog = async () => {
      try {
        const data = await getStoreProducts(buildProductParams());
        if (active) {
          setProducts(data.products || []);
          setAvailableBrands(data.brands || []);
          setError("");
        }
      } catch (err) {
        console.error(err);
        if (active) {
          setError("Unable to load the product catalog. Please try again.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    fetchCatalog();
    return () => {
      active = false;
    };
  }, [buildProductParams]);

  const updateUrlFilters = (nextCategory, nextQuery) => {
    const params = new URLSearchParams();
    if (nextCategory) {
      params.set("category", nextCategory);
    }
    if (nextQuery && nextQuery.trim()) {
      params.set("q", nextQuery.trim());
    }
    setSearchParams(params);
  };

  const resetAllFilters = () => {
    setSearchInput("");
    setBrandFilter("");
    setMaxPrice("");
    setInStockOnly(false);
    setSortBy("featured");
    setSearchParams(new URLSearchParams());
  };

  const showHero = !selectedCategory && !urlQuery;

  return (
    <div className="sg-container">
      {showHero && (
        <>
          <section className="sg-hero" aria-label="Featured Hardware">
            <div className="sg-hero-card">
              <div>
                <span className="sg-hero-eyebrow">
                  <i className="bi bi-lightning-charge-fill"></i>
                  SORANOGEAR FLAGSHIP COLLECTION
                </span>
                <h1>
                  Precision Hardware for Modern Work &amp; Play.
                </h1>
                <p>
                  From ultralight productivity laptops and IPS studio monitors
                  to noise-cancelling wireless audio and tactile mechanical
                  keyboards—engineered to elevate every desk.
                </p>
                <div className="sg-hero-cta">
                  <button
                    type="button"
                    className="sg-btn-primary"
                    onClick={() =>
                      catalogRef.current?.scrollIntoView({ behavior: "smooth" })
                    }
                  >
                    Shop All Products
                    <i className="bi bi-arrow-down-right"></i>
                  </button>
                  <button
                    type="button"
                    className="sg-btn-ghost"
                    onClick={() => updateUrlFilters("Laptops", "")}
                  >
                    Explore Laptops
                  </button>
                </div>
              </div>

              <div className="sg-hero-visual">
                <Link to="/?category=Laptops" className="sg-hero-tile">
                  <img
                    src="/product-images/laptop-pro-14.jpg"
                    alt="Laptop Pro 14"
                    onError={handleProductImageError}
                  />
                  <div className="sg-hero-tile-caption">
                    <span>Pro Laptops</span>
                    <span>From ₹49,999 →</span>
                  </div>
                </Link>
                <Link to="/?category=Audio" className="sg-hero-tile">
                  <img
                    src="/product-images/wireless-earbuds.jpg"
                    alt="Wireless Audio"
                    onError={handleProductImageError}
                  />
                  <div className="sg-hero-tile-caption">
                    <span>ANC Audio</span>
                    <span>From ₹2,499 →</span>
                  </div>
                </Link>
                <Link
                  to="/?category=Gaming+Accessories"
                  className="sg-hero-tile"
                >
                  <img
                    src="/product-images/mechanical-keyboard.jpg"
                    alt="Mechanical Keyboards"
                    onError={handleProductImageError}
                  />
                  <div className="sg-hero-tile-caption">
                    <span>Gaming Gear</span>
                    <span>From ₹1,499 →</span>
                  </div>
                </Link>
                <Link
                  to="/?category=Monitors+%26+Displays"
                  className="sg-hero-tile"
                >
                  <img
                    src="/product-images/monitor-24.svg"
                    alt="IPS Monitors"
                    onError={handleProductImageError}
                  />
                  <div className="sg-hero-tile-caption">
                    <span>IPS Displays</span>
                    <span>₹9,999 →</span>
                  </div>
                </Link>
              </div>
            </div>
          </section>

          <section className="sg-trust-strip" aria-label="Store highlights">
            <div className="sg-trust-item">
              <span className="sg-trust-icon">
                <i className="bi bi-box-seam"></i>
              </span>
              <div>
                <strong>Live Stock Verification</strong>
                <span>Real-time warehouse inventory</span>
              </div>
            </div>
            <div className="sg-trust-item">
              <span className="sg-trust-icon">
                <i className="bi bi-truck"></i>
              </span>
              <div>
                <strong>Free Express Shipping</strong>
                <span>On all orders ₹1,999 and above</span>
              </div>
            </div>
            <div className="sg-trust-item">
              <span className="sg-trust-icon">
                <i className="bi bi-headset"></i>
              </span>
              <div>
                <strong>SoranoTech Support</strong>
                <span>Dedicated executive care team</span>
              </div>
            </div>
            <div className="sg-trust-item">
              <span className="sg-trust-icon">
                <i className="bi bi-shield-check"></i>
              </span>
              <div>
                <strong>Safe POC Checkout</strong>
                <span>Transparent order confirmation</span>
              </div>
            </div>
          </section>

          {categories.length > 0 && (
            <section className="mb-4">
              <div className="sg-section-header">
                <div>
                  <h2>Shop by Category</h2>
                  <p>Explore {categories.length} specialized hardware categories</p>
                </div>
              </div>
              <div className="sg-category-grid">
                {categories.map((cat) => (
                  <button
                    key={cat.name}
                    type="button"
                    className={`sg-category-card ${
                      selectedCategory === cat.name ? "active" : ""
                    }`}
                    onClick={() => updateUrlFilters(cat.name, urlQuery)}
                  >
                    <img
                      src={cat.image_url}
                      alt={cat.name}
                      loading="lazy"
                      onError={handleProductImageError}
                    />
                    <div className="sg-category-card-body">
                      <strong>{cat.name}</strong>
                      <small>
                        {cat.product_count}{" "}
                        {cat.product_count === 1 ? "product" : "products"} •
                        From {formatINR(cat.starting_price)}
                      </small>
                    </div>
                  </button>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      <section ref={catalogRef} className="pt-3">
        <div className="sg-section-header">
          <div>
            <h2>
              {selectedCategory
                ? selectedCategory
                : urlQuery
                  ? `Search Results for "${urlQuery}"`
                  : "All SoranoGear Products"}
            </h2>
            <p>
              {loading
                ? "Refreshing live inventory..."
                : `${products.length} ${
                    products.length === 1 ? "product" : "products"
                  } available`}
            </p>
          </div>
          {(selectedCategory ||
            urlQuery ||
            brandFilter ||
            maxPrice ||
            inStockOnly) && (
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={resetAllFilters}
            >
              <i className="bi bi-x-circle me-1"></i>
              Clear All Filters
            </button>
          )}
        </div>

        {/* Interactive Discovery & Filtering Toolbar */}
        <div className="sg-catalog-toolbar">
          <div className="sg-toolbar-filters">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                updateUrlFilters(selectedCategory, searchInput);
              }}
              className="d-flex gap-2"
            >
              <input
                type="search"
                className="sg-filter-input"
                placeholder="Filter by keyword..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
              <button type="submit" className="btn btn-sm btn-primary px-3">
                Apply
              </button>
            </form>

            <select
              className="sg-filter-select"
              aria-label="Filter by category"
              value={selectedCategory}
              onChange={(e) => updateUrlFilters(e.target.value, urlQuery)}
            >
              <option value="">All Categories</option>
              {categories.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>

            <select
              className="sg-filter-select"
              aria-label="Filter by brand"
              value={brandFilter}
              onChange={(e) => setBrandFilter(e.target.value)}
            >
              <option value="">All Brands</option>
              {availableBrands.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>

            <select
              className="sg-filter-select"
              aria-label="Budget ceiling"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
            >
              <option value="">Any Budget</option>
              <option value="2000">Under ₹2,000</option>
              <option value="3500">Under ₹3,500</option>
              <option value="10000">Under ₹10,000</option>
              <option value="50000">Under ₹50,000</option>
            </select>

            <label className="sg-stock-check">
              <input
                type="checkbox"
                checked={inStockOnly}
                onChange={(e) => setInStockOnly(e.target.checked)}
              />
              In Stock Only
            </label>
          </div>

          <div className="d-flex align-items-center gap-2">
            <label htmlFor="sg-sort" className="small text-muted fw-semibold">
              Sort:
            </label>
            <select
              id="sg-sort"
              className="sg-filter-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="featured">Featured</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
              <option value="name_asc">Name: A to Z</option>
              <option value="stock_desc">Availability</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="alert alert-warning d-flex align-items-center justify-content-between">
            <span>{error}</span>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              onClick={loadProducts}
            >
              Retry
            </button>
          </div>
        )}

        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border text-primary" role="status"></div>
            <p className="text-muted mt-2">Loading SoranoGear catalog...</p>
          </div>
        ) : products.length === 0 ? (
          <div className="sg-panel text-center py-5 mb-5">
            <i
              className="bi bi-search text-muted"
              style={{ fontSize: "38px" }}
            ></i>
            <h3 className="mt-3 fs-5 fw-bold">No matching products found</h3>
            <p className="text-muted small mt-1 mb-3">
              Try broadening your search terms or clearing active category/price
              filters.
            </p>
            <button
              type="button"
              className="sg-btn-primary"
              onClick={resetAllFilters}
            >
              Show All Products
            </button>
          </div>
        ) : (
          <div className="sg-product-grid">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default StoreHomePage;
