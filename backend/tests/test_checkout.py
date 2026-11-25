def _sample_checkout_payload(product_id: int, qty: int = 2, **overrides):
    base = {
        "items": [{"product_id": product_id, "quantity": qty}],
        "customer_full_name": "Rohan Verma",
        "customer_email": "rohan.verma@example.com",
        "customer_phone": "+919876543210",
        "shipping_address": {
            "line1": "12 Jubilee Hills Road",
            "line2": "Apt 3B",
            "city": "Hyderabad",
            "state": "Telangana",
            "postal_code": "500033",
            "country": "India",
        },
        "same_as_shipping": True,
        "payment_method": "MOCK_CARD",
        "notes": "Ring bell once",
        "idempotency_key": "chk-idem-key-0001",
    }
    base.update(overrides)
    return base


def test_cart_validation_and_authenticated_cart_sync(api_env):
    client = api_env["client"]
    headers = api_env["customer_headers"]
    earbuds = api_env["products"]["earbuds"]
    oos_laptop = api_env["products"]["laptop_oos"]

    # Validate cart caps quantity at available stock and warns on out-of-stock
    val_res = client.post(
        "/api/store/cart/validate",
        json={
            "items": [
                {"product_id": earbuds.id, "quantity": 2},
                {"product_id": oos_laptop.id, "quantity": 1},
            ]
        },
    )
    assert val_res.status_code == 200
    val_body = val_res.json()
    assert val_body["subtotal_amount"] == 4998.0
    assert val_body["shipping_amount"] == 0.0  # Free shipping >= 1999
    assert len(val_body["warnings"]) >= 1

    # Sync cart for logged-in customer
    put_res = client.put(
        "/api/store/cart",
        headers=headers,
        json={"items": [{"product_id": earbuds.id, "quantity": 3}]},
    )
    assert put_res.status_code == 200
    assert put_res.json()["item_count"] == 3

    get_res = client.get("/api/store/cart", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["item_count"] == 3


def test_guest_checkout_decrements_stock_is_idempotent_and_deduplicates_repeat_customer(
    api_env,
):
    client = api_env["client"]
    support_headers = api_env["support_headers"]
    earbuds = api_env["products"]["earbuds"]

    payload = _sample_checkout_payload(earbuds.id, qty=2, idempotency_key="idem-guest-1")
    res1 = client.post("/api/store/checkout", json=payload)
    assert res1.status_code == 200
    order1 = res1.json()
    assert order1["order_number"].startswith("ORD-")
    assert order1["order_number"].endswith(f"-{order1['id']:04d}")
    assert order1["payment_method"] == "MOCK_CARD"
    assert order1["payment_status"] == "PAID"
    assert order1["payment_reference"].startswith("MOCK-CARD-")
    assert order1["total_amount"] == 4998.0

    # Retrying with identical idempotency_key does not double-charge or double-decrement stock
    res_dup = client.post("/api/store/checkout", json=payload)
    assert res_dup.status_code == 200
    assert res_dup.json()["id"] == order1["id"]

    # Stock decreased from 12 -> 10 (only once!)
    prod_detail = client.get(f"/api/store/products/{earbuds.id}").json()["product"]
    assert prod_detail["stock"] == 10

    # Second order from same guest email reuses existing customer record instead of duplicating
    payload2 = _sample_checkout_payload(
        earbuds.id,
        qty=1,
        payment_method="MOCK_COD",
        idempotency_key="idem-guest-2",
    )
    res2 = client.post("/api/store/checkout", json=payload2)
    assert res2.status_code == 200
    order2 = res2.json()
    assert order2["customer_id"] == order1["customer_id"]
    assert order2["order_number"].endswith(f"-{order2['id']:04d}")
    assert order2["payment_status"] == "PENDING"  # COD stays PENDING until delivery

    # Verify executive customer directory shows 1 deduplicated Rohan Verma with 2 orders
    cust_list = client.get(
        "/api/admin/customers",
        headers=support_headers,
        params={"search": "rohan.verma@example.com"},
    ).json()
    assert cust_list["total"] == 1
    assert cust_list["customers"][0]["total_orders"] == 2


def test_checkout_rejects_insufficient_or_out_of_stock_without_partial_writes(api_env):
    client = api_env["client"]
    keyboard = api_env["products"]["keyboard"]  # stock = 3
    oos_laptop = api_env["products"]["laptop_oos"]  # stock = 0

    # Requesting 5 when only 3 in stock -> 409 Conflict, stock remains untouched at 3
    over_res = client.post(
        "/api/store/checkout",
        json=_sample_checkout_payload(keyboard.id, qty=5, idempotency_key="idem-over-1"),
    )
    assert over_res.status_code == 409
    assert (
        client.get(f"/api/store/products/{keyboard.id}").json()["product"]["stock"] == 3
    )

    # Requesting out-of-stock item -> 409 Conflict
    oos_res = client.post(
        "/api/store/checkout",
        json=_sample_checkout_payload(oos_laptop.id, qty=1, idempotency_key="idem-oos-1"),
    )
    assert oos_res.status_code == 409
