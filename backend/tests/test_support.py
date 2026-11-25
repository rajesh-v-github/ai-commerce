def test_existing_support_endpoints_remain_intact_for_executives(api_env):
    """Verify existing Customer Support Executive endpoints continue working with exact contract."""
    client = api_env["client"]
    support_headers = api_env["support_headers"]
    customer_user = api_env["customer_user"]
    earbuds = api_env["products"]["earbuds"]

    # Unauthenticated spoofing of a password-registered account email is rejected (409)
    spoof_res = client.post(
        "/api/store/checkout",
        json={
            "items": [{"product_id": earbuds.id, "quantity": 1}],
            "customer_full_name": customer_user.full_name,
            "customer_email": customer_user.email,
            "customer_phone": customer_user.phone,
            "shipping_address": {
                "line1": "Plot 10, HITEC City",
                "city": "Hyderabad",
                "state": "Telangana",
                "postal_code": "500081",
                "country": "India",
            },
            "same_as_shipping": True,
            "payment_method": "MOCK_CARD",
            "idempotency_key": "idem-support-spoof-1",
        },
    )
    assert spoof_res.status_code == 409

    # Authenticated checkout succeeds and populates support endpoints
    chk = client.post(
        "/api/store/checkout",
        headers=api_env["customer_headers"],
        json={
            "items": [{"product_id": earbuds.id, "quantity": 1}],
            "customer_full_name": customer_user.full_name,
            "customer_email": customer_user.email,
            "customer_phone": customer_user.phone,
            "shipping_address": {
                "line1": "Plot 10, HITEC City",
                "city": "Hyderabad",
                "state": "Telangana",
                "postal_code": "500081",
                "country": "India",
            },
            "same_as_shipping": True,
            "payment_method": "MOCK_CARD",
            "idempotency_key": "idem-support-compat-1",
        },
    ).json()
    order_number = chk["order_number"]

    # 1. Existing Support Dashboard Overview (/api/dashboard/overview)
    dash = client.get("/api/dashboard/overview", headers=support_headers)
    assert dash.status_code == 200
    dash_data = dash.json()
    assert "attention_tickets" in dash_data
    assert "order_status_counts" in dash_data
    assert "recent_orders" in dash_data

    # 2. Existing Order Details by number (/api/orders/number/{order_number})
    ord_detail = client.get(
        f"/api/orders/number/{order_number}", headers=support_headers
    )
    assert ord_detail.status_code == 200
    assert ord_detail.json()["order_number"] == order_number
    assert len(ord_detail.json()["items"]) == 1

    # 3. Existing Support Tickets list & ticket detail
    tickets = client.get("/api/tickets/", headers=support_headers)
    assert tickets.status_code == 200
    assert len(tickets.json()) >= 1
    assert tickets.json()[0]["ticket_number"] == "TKT-001"

    # 4. Existing Support Customers list (/api/customer/) & search (/api/customer/search)
    custs = client.get("/api/customer/", headers=support_headers)
    assert custs.status_code == 200
    assert any(c["username"] == "aarav_cust" for c in custs.json())

    search = client.post(
        "/api/customer/search",
        headers=support_headers,
        json={"search": "aarav"},
    )
    assert search.status_code == 200
    assert search.json()["username"] == "aarav_cust"

    # 5. Existing Products tab endpoint (/api/products/)
    prods = client.get("/api/products/")
    assert prods.status_code == 200
    assert any(p["name"] == "Wireless Earbuds" for p in prods.json())


def test_support_copilot_tools_and_ticket_summary_work_when_ollama_offline(
    api_env, monkeypatch
):
    client = api_env["client"]
    support_headers = api_env["support_headers"]
    customer_user = api_env["customer_user"]

    def raise_ollama_down(_prompt):
        raise ConnectionError("Failed to connect to Ollama")

    monkeypatch.setattr("app.agents.tools.ask_llm", raise_ollama_down)

    # 1. Product Lookup ("Give me wireless products")
    lookup_res = client.post(
        "/api/copilot/assistant",
        headers=support_headers,
        json={"feature": "product_lookup", "question": "Give me wireless products"},
    )
    assert lookup_res.status_code == 200
    assert "Wireless Earbuds" in lookup_res.json()["answer"]
    assert "Price: ₹" in lookup_res.json()["answer"]

    # 2. Product Recommendations
    rec_res = client.post(
        "/api/copilot/assistant",
        headers=support_headers,
        json={
            "feature": "product_recommendation",
            "question": "Recommend wireless audio products",
        },
    )
    assert rec_res.status_code == 200
    assert "Product: Wireless Earbuds" in rec_res.json()["recommendation"]
    assert "Reason:" in rec_res.json()["recommendation"]

    # 3. Place an order, then test Order Lookup (free-form question)
    earbuds = api_env["products"]["earbuds"]
    chk = client.post(
        "/api/store/checkout",
        headers=api_env["customer_headers"],
        json={
            "items": [{"product_id": earbuds.id, "quantity": 1}],
            "customer_full_name": customer_user.full_name,
            "customer_email": customer_user.email,
            "customer_phone": customer_user.phone,
            "shipping_address": {
                "line1": "Plot 10, HITEC City",
                "city": "Hyderabad",
                "state": "Telangana",
                "postal_code": "500081",
                "country": "India",
            },
            "same_as_shipping": True,
            "payment_method": "MOCK_CARD",
            "idempotency_key": "idem-offline-copilot-1",
        },
    ).json()

    ord_res = client.post(
        "/api/copilot/assistant",
        headers=support_headers,
        json={
            "feature": "order_lookup",
            "customer_id": customer_user.id,
            "question": "What is the status of the latest order?",
        },
    )
    assert ord_res.status_code == 200
    assert f"Order: {chk['order_number']}" in ord_res.json()["answer"]

    # 4. Create Ticket draft
    draft_res = client.post(
        "/api/copilot/assistant",
        headers=support_headers,
        json={
            "feature": "create_ticket",
            "question": "Customer received a damaged item and wants a replacement.",
        },
    )
    assert draft_res.status_code == 200
    assert draft_res.json()["ticket_preview"]["priority"] == "HIGH"

    # 5. Ticket Summary (/api/copilot/insights)
    insights_res = client.post(
        "/api/copilot/insights",
        headers=support_headers,
        json={"ticket_number": "TKT-001"},
    )
    assert insights_res.status_code == 200
    payload = insights_res.json()
    assert payload["executive_summary"]["ticket_number"] == "TKT-001"
    assert payload["executive_summary"]["issue_summary"]
    assert payload["draft_response"]["ai_response"]

