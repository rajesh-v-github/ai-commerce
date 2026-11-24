from app.models.product import Product


def test_storefront_products_exclude_inactive_and_support_filters(api_env):
    client = api_env["client"]

    # Default listing includes active products (both in-stock and out-of-stock) and excludes inactive
    res = client.get("/api/store/products")
    assert res.status_code == 200
    body = res.json()
    names = [p["name"] for p in body["products"]]
    assert "Wireless Earbuds" in names
    assert "Mechanical Keyboard" in names
    assert "Gaming Laptop X" in names
    assert "Archived Adapter" not in names

    # Category filter
    cat_res = client.get("/api/store/products", params={"category": "Audio"})
    assert cat_res.status_code == 200
    assert [p["name"] for p in cat_res.json()["products"]] == ["Wireless Earbuds"]

    # In-stock filter excludes 0-stock items
    stock_res = client.get("/api/store/products", params={"in_stock": True})
    assert stock_res.status_code == 200
    in_stock_names = [p["name"] for p in stock_res.json()["products"]]
    assert "Gaming Laptop X" not in in_stock_names
    assert "Wireless Earbuds" in in_stock_names

    # Search + max_price filter
    search_res = client.get(
        "/api/store/products", params={"q": "keyboard", "max_price": 4000}
    )
    assert search_res.status_code == 200
    assert [p["name"] for p in search_res.json()["products"]] == ["Mechanical Keyboard"]


def test_storefront_categories_and_product_detail_related_items(api_env):
    client = api_env["client"]
    earbuds_id = api_env["products"]["earbuds"].id
    inactive_id = api_env["products"]["inactive"].id

    cats = client.get("/api/store/categories")
    assert cats.status_code == 200
    cat_names = [c["name"] for c in cats.json()]
    assert "Audio" in cat_names
    assert "Computer Accessories" not in cat_names  # Only had inactive product

    detail = client.get(f"/api/store/products/{earbuds_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["product"]["name"] == "Wireless Earbuds"
    assert payload["product"]["image_url"] == "/product-images/wireless-earbuds.jpg"
    assert isinstance(payload["related_products"], list)

    # Inactive products return 404 on public storefront
    hidden = client.get(f"/api/store/products/{inactive_id}")
    assert hidden.status_code == 404


def test_ensure_catalog_defaults_never_overwrites_custom_product_images(api_env):
    client = api_env["client"]
    db = api_env["db_factory"]()
    try:
        prod = db.query(Product).filter(Product.name == "Wireless Earbuds").first()
        prod.image_url = "https://cdn.example.com/custom-earbuds-photo.png"
        db.commit()
        earbuds_id = prod.id
    finally:
        db.close()

    # Trigger storefront read which calls ensure_catalog_defaults
    detail = client.get(f"/api/store/products/{earbuds_id}")
    assert detail.status_code == 200
    assert (
        detail.json()["product"]["image_url"]
        == "https://cdn.example.com/custom-earbuds-photo.png"
    )
