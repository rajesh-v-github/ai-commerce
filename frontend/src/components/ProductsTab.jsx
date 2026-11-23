import { useEffect, useState } from "react";

import { getProducts } from "../services/productService";

function ProductsTab() {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");

  useEffect(() => {
    const loadProducts = async () => {
      try {
        const data = await getProducts();

        setProducts(data);
      } catch (error) {
        console.error(error);
      }
    };

    loadProducts();
  }, []);

  const filteredProducts = products.filter((product) =>
    (product.name || "")
      .toLowerCase()
      .includes(appliedSearch.trim().toLowerCase()),
  );

  return (
    <div>
      <div className="card mb-3">
        <div className="card-header">Product Search</div>
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
              placeholder="Search by product name"
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
        <div className="card-header">Products</div>

        <div className="card-body">
          <table className="table table-striped table-hover">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Category</th>
                <th>Price</th>
                <th>Stock</th>
              </tr>
            </thead>

            <tbody>
              {filteredProducts.length > 0 ? (
                filteredProducts.map((product) => (
                  <tr key={product.id}>
                    <td>{product.id}</td>

                    <td>{product.name}</td>

                    <td>{product.category}</td>

                    <td>₹{product.price}</td>

                    <td>{product.stock}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="text-center text-muted">
                    {appliedSearch.trim()
                      ? `No products found matching "${appliedSearch}".`
                      : "No products available."}
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

export default ProductsTab;
