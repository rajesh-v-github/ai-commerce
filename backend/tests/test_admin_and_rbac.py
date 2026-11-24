import io
from app.services.ollama_service import AIServiceUnavailableError


def test_rbac_blocks_unauthenticated_and_customer_users_from_executive_endpoints(
    api_env,
):
    client = api_env["client"]
    cust_headers = api_env["customer_headers"]
    other_customer = api_env["other_customer"]

    admin_endpoints = [
        ("GET", "/api/admin/dashboard", None),
        ("GET", "/api/admin/products", None),
        (
            "POST",
            "/api/admin/products",
            {
                "name": "Unauthorized Item",
                "category": "Audio",
                "price": 999,
                "stock": 5,
            },
        ),
        ("GET", "/api/admin/orders", None),
        ("GET", "/api/admin/customers", None),
        (
            "POST",
            "/api/admin/products/generate-description",
            {"name": "Test Gear", "category": "Audio"},
        ),
    ]

    for method, url, payload in admin_endpoints:
        # Unauthenticated -> 401 or 403 (HTTPBearer rejects missing token)
        unauth_res = client.request(method, url, json=payload)
        assert unauth_res.status_code in (401, 403), f"Expected 401/403 for {method} {url}"

        # Customer role -> 403 Forbidden
        cust_res = client.request(method, url, headers=cust_headers, json=payload)
        assert cust_res.status_code == 403, f"Expected 403 for customer on {method} {url}"

    # Hardened legacy endpoints also block customer accounts
    assert (
        client.post(
            "/api/products/products",
            headers=cust_headers,
            json={
                "name": "Blocked",
                "description": "x",
                "category": "Audio",
                "price": 100,
                "stock": 1,
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/customer/search",
            headers=cust_headers,
            json={"username": "meera"},
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/orders/customer/{other_customer.id}",
            headers=cust_headers,
        ).status_code
        == 403
    )


def test_public_registration_always_creates_customer_never_executive(api_env):
    client = api_env["client"]

    reg = client.post(
        "/api/auth/register",
        json={
            "username": "new_shopper",
            "full_name": "New Shopper",
            "email": "shopper@example.com",
            "phone": "+919811122233",
            "password": "SafePassword123!",
            "role": "support",  # Even if attacker injects role="support", schema ignores it
        },
    )
    assert reg.status_code in (200, 201)
    data = reg.json()
    assert data["role"] == "customer"

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["role"] == "customer"


def test_admin_dashboard_kpis_product_crud_soft_delete_and_image_upload(api_env):
    client = api_env["client"]
    support_headers = api_env["support_headers"]
    earbuds = api_env["products"]["earbuds"]

    # Place one order on earbuds so earbuds is referenced by OrderItem
    client.post(
        "/api/store/checkout",
        json={
            "items": [{"product_id": earbuds.id, "quantity": 2}],
            "customer_full_name": "Priya Nair",
            "customer_email": "priya@example.com",
            "customer_phone": "+919800011122",
            "shipping_address": {
                "line1": "MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "postal_code": "560001",
                "country": "India",
            },
            "same_as_shipping": True,
            "payment_method": "MOCK_CARD",
            "idempotency_key": "idem-admin-kpi-1",
        },
    )

    # 1. Verify Admin Overview KPIs reflect real DB state
    overview = client.get("/api/admin/dashboard?days=14", headers=support_headers)
    assert overview.status_code == 200
    ov = overview.json()
    assert ov["kpis"]["total_revenue"] == 4998.0
    assert ov["kpis"]["total_orders"] == 1
    assert ov["kpis"]["low_stock_count"] == 1  # Mechanical Keyboard (stock=3 <= 5)
    assert ov["kpis"]["out_of_stock_count"] == 1  # Gaming Laptop X (stock=0)
    assert ov["best_selling_products"][0]["name"] == "Wireless Earbuds"
    assert ov["best_selling_products"][0]["units_sold"] == 2

    # 2. Upload product image
    svg_bytes = b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"></svg>'
    upload_res = client.post(
        "/api/admin/products/upload-image",
        headers=support_headers,
        files={"file": ("test-icon.svg", io.BytesIO(svg_bytes), "image/svg+xml")},
    )
    assert upload_res.status_code == 200
    uploaded_url = upload_res.json()["image_url"]
    assert uploaded_url.startswith("/api/uploads/products/")

    # 3. Create new product, update stock, then delete unused product permanently
    created = client.post(
        "/api/admin/products",
        headers=support_headers,
        json={
            "name": "Thunderbolt 4 Dock",
            "description": "12-port aluminum dock.",
            "category": "Computer Accessories",
            "sku": "SG-DOC-900",
            "price": 8999.0,
            "stock": 8,
            "low_stock_threshold": 3,
            "image_url": uploaded_url,
            "is_active": True,
        },
    )
    assert created.status_code == 200
    dock_id = created.json()["id"]

    inv = client.patch(
        f"/api/admin/products/{dock_id}/inventory",
        headers=support_headers,
        json={"stock": 20, "low_stock_threshold": 4},
    )
    assert inv.status_code == 200
    assert inv.json()["stock"] == 20

    # Unused product -> permanently deleted
    del_unused = client.delete(
        f"/api/admin/products/{dock_id}", headers=support_headers
    )
    assert del_unused.status_code == 200
    assert del_unused.json()["action"] == "deleted"

    # Product referenced in historical orders -> safely soft-deactivated to preserve order integrity
    del_referenced = client.delete(
        f"/api/admin/products/{earbuds.id}", headers=support_headers
    )
    assert del_referenced.status_code == 200
    assert del_referenced.json()["action"] == "deactivated"
    assert del_referenced.json()["product"]["is_active"] is False


def test_ai_product_description_generation_and_graceful_unavailable_handling(
    api_env, monkeypatch
):
    client = api_env["client"]
    support_headers = api_env["support_headers"]
    earbuds = api_env["products"]["earbuds"]

    captured_prompts = []

    def fake_ollama_call(prompt: str, **_kwargs):
        captured_prompts.append(prompt)
        return (
            "Experience crisp everyday audio with the Wireless Earbuds, crafted for "
            "commuters and remote professionals seeking tangle-free Bluetooth convenience."
        )

    monkeypatch.setattr(
        "app.services.ollama_service._call_ollama", fake_ollama_call
    )

    gen_res = client.post(
        "/api/admin/products/generate-description",
        headers=support_headers,
        json={
            "name": "Wireless Earbuds",
            "category": "Audio",
            "features": "Bluetooth connectivity, compact charging case",
            "tone": "balanced",
        },
    )
    assert gen_res.status_code == 200
    gen_body = gen_res.json()
    assert "Wireless Earbuds" in gen_body["description"]
    assert gen_body["provider"] == "ollama"
    assert len(captured_prompts) == 1
    assert "NEVER invent" in captured_prompts[0]

    # Generating an AI draft does NOT mutate DB product description until executive saves
    db_prod = client.get("/api/admin/products", headers=support_headers).json()[
        "products"
    ]
    earbuds_row = next(p for p in db_prod if p["id"] == earbuds.id)
    assert earbuds_row["description"] == "Compact ANC Bluetooth 5.3 wireless earbuds."

    # Simulate AI service offline -> returns clean HTTP 503 with actionable message
    def fake_offline(*_args, **_kwargs):
        raise AIServiceUnavailableError(
            "AI description service is currently unavailable."
        )

    monkeypatch.setattr("app.api.admin.generate_product_description", fake_offline)
    offline_res = client.post(
        "/api/admin/products/generate-description",
        headers=support_headers,
        json={"name": "Wireless Earbuds", "category": "Audio"},
    )
    assert offline_res.status_code == 503
    assert "unavailable" in offline_res.json()["detail"].lower()


def test_x_auth_token_header_works_when_proxy_strips_or_overwrites_authorization(
    api_env,
):
    client = api_env["client"]
    customer_headers = api_env["customer_headers"]
    support_headers = api_env["support_headers"]
    raw_customer_jwt = customer_headers["Authorization"].split(" ", 1)[1]
    raw_support_jwt = support_headers["Authorization"].split(" ", 1)[1]

    # 1. Proxy stripped Authorization completely; only X-Auth-Token reaches FastAPI
    me_res = client.get("/api/auth/me", headers={"X-Auth-Token": raw_customer_jwt})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "aarav_cust"

    cart_res = client.get("/api/store/cart", headers={"X-Auth-Token": raw_customer_jwt})
    assert cart_res.status_code == 200

    # 2. Proxy overwrote Authorization with upstream gateway auth, while X-Auth-Token holds app JWT
    admin_res = client.get(
        "/api/admin/dashboard",
        headers={
            "Authorization": "Basic Z2F0ZXdheTpwYXNz",
            "X-Auth-Token": raw_support_jwt,
        },
    )
    assert admin_res.status_code == 200
    assert "kpis" in admin_res.json()


def test_auto_serial_sku_generation_on_create_and_category_update(api_env):
    client = api_env["client"]
    support_headers = api_env["support_headers"]

    listing = client.get("/api/admin/products", headers=support_headers).json()
    next_serial = listing["next_sku_serial"]

    created = client.post(
        "/api/admin/products",
        headers=support_headers,
        json={
            "name": "Studio Condenser Headset",
            "description": "Broadcast USB-C headset",
            "category": "Audio",
            "price": 5499.0,
            "stock": 12,
            "low_stock_threshold": 4,
            "is_active": True,
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["sku"] == f"SG-AUD-{next_serial:03d}"

    # Updating category updates the 3-letter prefix while preserving its serial number
    updated = client.put(
        f"/api/admin/products/{body['id']}",
        headers=support_headers,
        json={"category": "Gaming Accessories"},
    )
    assert updated.status_code == 200
    assert updated.json()["sku"] == f"SG-GAM-{next_serial:03d}"


def test_ai_description_generator_falls_back_gracefully_across_all_tones_when_ollama_down(
    api_env, monkeypatch
):
    client = api_env["client"]
    support_headers = api_env["support_headers"]

    def ollama_down(*_args, **_kwargs):
        raise ConnectionError("Failed to connect to Ollama")

    monkeypatch.setattr("app.services.ollama_service._call_ollama", ollama_down)

    outputs = set()
    for tone in ("balanced", "concise", "premium", "technical"):
        res = client.post(
            "/api/admin/products/generate-description",
            headers=support_headers,
            json={
                "name": "Gaming Laptop X",
                "category": "Laptops",
                "attributes": "High performance gaming laptop",
                "features": "RGB backlit deck, dual-fan cooling",
                "tone": tone,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "Gaming Laptop X" in data["description"]
        assert "RGB backlit deck" in data["description"]
        assert data["provider"] == "builtin-ai"
        outputs.add(data["description"])

    assert len(outputs) == 4



