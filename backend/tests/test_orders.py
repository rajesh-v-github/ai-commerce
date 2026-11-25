def test_authenticated_customer_order_history_confirmation_and_isolation(api_env):
    client = api_env["client"]
    cust_headers = api_env["customer_headers"]
    other_headers = api_env["other_customer_headers"]
    earbuds = api_env["products"]["earbuds"]

    chk = client.post(
        "/api/store/checkout",
        headers=cust_headers,
        json={
            "items": [{"product_id": earbuds.id, "quantity": 1}],
            "customer_full_name": "Aarav Sharma",
            "customer_email": "aarav@example.com",
            "customer_phone": "+919999900002",
            "shipping_address": {
                "line1": "Plot 10, HITEC City",
                "city": "Hyderabad",
                "state": "Telangana",
                "postal_code": "500081",
                "country": "India",
            },
            "same_as_shipping": True,
            "payment_method": "MOCK_UPI",
            "idempotency_key": "idem-auth-order-1",
        },
    )
    assert chk.status_code == 200
    created_order = chk.json()
    order_number = created_order["order_number"]
    payment_ref = created_order["payment_reference"]

    # Order confirmation works via payment reference token (even unauthenticated)
    conf_ok = client.get(
        f"/api/store/orders/confirmation/{order_number}",
        params={"ref": payment_ref},
    )
    assert conf_ok.status_code == 200
    assert conf_ok.json()["order_number"] == order_number

    # Unauthenticated request without valid ref token is denied (403)
    conf_denied = client.get(f"/api/store/orders/confirmation/{order_number}")
    assert conf_denied.status_code == 403

    # Other authenticated customer cannot read Aarav's confirmation or customer orders
    other_conf = client.get(
        f"/api/store/orders/confirmation/{order_number}",
        headers=other_headers,
    )
    assert other_conf.status_code == 403

    # Aarav sees the order in /api/orders/my, while Meera sees empty list
    my_orders = client.get("/api/orders/my", headers=cust_headers)
    assert my_orders.status_code == 200
    assert len(my_orders.json()) == 1
    assert my_orders.json()[0]["order_number"] == order_number

    other_orders = client.get("/api/orders/my", headers=other_headers)
    assert other_orders.status_code == 200
    assert other_orders.json() == []


def test_admin_order_lifecycle_audit_trail_and_cancellation_stock_restoration(api_env):
    client = api_env["client"]
    cust_headers = api_env["customer_headers"]
    support_headers = api_env["support_headers"]
    keyboard = api_env["products"]["keyboard"]  # initial stock = 3

    # Customer buys 2 keyboards -> stock drops from 3 to 1
    chk = client.post(
        "/api/store/checkout",
        headers=cust_headers,
        json={
            "items": [{"product_id": keyboard.id, "quantity": 2}],
            "customer_full_name": "Aarav Sharma",
            "customer_email": "aarav@example.com",
            "customer_phone": "+919999900002",
            "shipping_address": {
                "line1": "Plot 10, HITEC City",
                "city": "Hyderabad",
                "state": "Telangana",
                "postal_code": "500081",
                "country": "India",
            },
            "same_as_shipping": True,
            "payment_method": "MOCK_CARD",
            "idempotency_key": "idem-lifecycle-1",
        },
    ).json()
    order_id = chk["id"]
    assert (
        client.get(f"/api/store/products/{keyboard.id}").json()["product"]["stock"] == 1
    )

    # Support executive transitions PROCESSING -> CONFIRMED -> SHIPPED
    conf_res = client.patch(
        f"/api/admin/orders/{order_id}/status",
        headers=support_headers,
        json={"status": "CONFIRMED", "note": "Verified warehouse pick"},
    )
    assert conf_res.status_code == 200
    assert conf_res.json()["status"] == "CONFIRMED"

    ship_res = client.patch(
        f"/api/admin/orders/{order_id}/status",
        headers=support_headers,
        json={"status": "SHIPPED", "note": "Dispatched via BlueDart"},
    )
    assert ship_res.status_code == 200
    assert ship_res.json()["status"] == "SHIPPED"

    # Cancelling the order restores the 2 keyboards back to stock (1 -> 3) and marks PAID -> REFUNDED
    cancel_res = client.patch(
        f"/api/admin/orders/{order_id}/status",
        headers=support_headers,
        json={"status": "CANCELLED", "note": "Customer requested cancellation"},
    )
    assert cancel_res.status_code == 200
    cancelled = cancel_res.json()
    assert cancelled["status"] == "CANCELLED"
    assert cancelled["payment_status"] == "REFUNDED"
    assert len(cancelled["status_history"]) == 4  # initial + CONFIRMED + SHIPPED + CANCELLED
    assert (
        client.get(f"/api/store/products/{keyboard.id}").json()["product"]["stock"] == 3
    )
