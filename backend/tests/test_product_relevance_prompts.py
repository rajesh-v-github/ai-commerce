import app.agents.tools as tools


PRODUCTS = [
    {
        "name": "Laptop Pro 14",
        "category": "Laptops",
        "description": "Business productivity laptop",
        "price": 49999,
        "stock": 12,
    },
    {
        "name": "Gaming Laptop X",
        "category": "Laptops",
        "description": "High performance gaming laptop",
        "price": 89999,
        "stock": 8,
    },
    {
        "name": "Laptop Backpack",
        "category": "Laptop Bags & Cases",
        "description": "Business laptop backpack",
        "price": 1999,
        "stock": 25,
    },
    {
        "name": "USB-C Hub",
        "category": "Computer Accessories",
        "description": "7-in-1 USB-C Hub",
        "price": 2499,
        "stock": 15,
    },
]


def test_product_lookup_prompt_compares_category_and_excludes_unrequested_accessories(
    monkeypatch,
):
    prompts = []
    monkeypatch.setattr(tools, "get_products", lambda db: PRODUCTS)
    monkeypatch.setattr(
        tools,
        "ask_llm",
        lambda prompt: prompts.append(prompt) or "Product: Laptop Pro 14",
    )

    answer = tools.generate_product_lookup(None, "What laptop products are available?")

    assert "Product: Laptop Pro 14" in answer
    assert len(prompts) == 1
    assert "Category: Laptops" in prompts[0]
    assert "Laptop Backpack" not in prompts[0]
    assert "The backend has shortlisted the catalog entries relevant to the question." in prompts[0]
    assert "Treat this list as the complete allowed result set." in prompts[0]


def test_recommendation_prompt_matches_product_type_and_constraints(monkeypatch):
    prompts = []
    monkeypatch.setattr(tools, "get_products", lambda db: PRODUCTS)
    monkeypatch.setattr(
        tools,
        "ask_llm",
        lambda prompt: prompts.append(prompt) or "Product: Laptop Pro 14",
    )

    answer = tools.generate_product_recommendation(
        None, "Recommend a laptop under 50000 for business."
    )

    assert answer.startswith("Product: Laptop Pro 14\nCategory: Laptops")
    assert "Price: ₹49999" in answer
    assert len(prompts) == 1
    assert "Category: Laptops" in prompts[0]
    assert "Laptop Backpack" not in prompts[0]
    assert "Treat this list as the complete allowed recommendation set." in prompts[0]
    assert "Gaming Laptop X" not in prompts[0]
    assert '"reason":"brief factual match"' in prompts[0]
    assert "Return only valid JSON with this shape" in prompts[0]


def test_lower_price_recommendations_are_deduplicated_and_sorted(monkeypatch):
    duplicate_response = (
        "Rec 1. **### Gaming Laptop X**\n"
        "Rec 2. **### Laptop Pro 14**\n"
        "Rec 3. **### Gaming Laptop X**\n"
        "Rec 4. **### Laptop Pro 14**"
    )
    monkeypatch.setattr(tools, "get_products", lambda db: PRODUCTS)
    monkeypatch.setattr(tools, "ask_llm", lambda prompt: duplicate_response)

    answer = tools.generate_product_recommendation(
        None, "Recommend a laptop which is less in price."
    )

    assert answer.count("Product: Laptop Pro 14") == 1
    assert answer.count("Product: Gaming Laptop X") == 1
    assert answer.index("Product: Laptop Pro 14") < answer.index(
        "Product: Gaming Laptop X"
    )


def test_recommendation_json_is_validated_and_deduplicated(monkeypatch):
    monkeypatch.setattr(tools, "get_products", lambda db: PRODUCTS)
    monkeypatch.setattr(
        tools,
        "ask_llm",
        lambda prompt: (
            '{"recommendations": ['
            '{"product": "Gaming Laptop X", "reason": "Gaming performance"},'
            '{"product": "Gaming Laptop X", "reason": "Duplicate"},'
            '{"product": "Unknown Laptop", "reason": "Not in catalog"},'
            '{"product": "Laptop Pro 14", "reason": "Business use"}]}'
        ),
    )

    answer = tools.generate_product_recommendation(
        None, "Recommend laptops."
    )

    assert answer.count("Product: Gaming Laptop X") == 1
    assert answer.count("Product: Laptop Pro 14") == 1
    assert "Unknown Laptop" not in answer
    assert answer.index("Product: Laptop Pro 14") < answer.index(
        "Product: Gaming Laptop X"
    )


def test_wireless_lookup_shortlists_only_wireless_products(monkeypatch):
    wireless_products = [
        {
            "name": "Wireless Earbuds",
            "category": "Audio",
            "description": "Bluetooth earbuds with noise cancellation",
            "price": 2499,
            "stock": 40,
        },
        {
            "name": "Bluetooth Speaker",
            "category": "Audio",
            "description": "Portable bluetooth speaker",
            "price": 2999,
            "stock": 20,
        },
        {
            "name": "Gaming Mouse",
            "category": "Gaming Accessories",
            "description": "RGB gaming mouse",
            "price": 1499,
            "stock": 50,
        },
        {
            "name": "Laptop Backpack",
            "category": "Laptop Bags & Cases",
            "description": "Business laptop backpack",
            "price": 1999,
            "stock": 25,
        },
        {
            "name": "Wireless Keyboard",
            "category": "Keyboards & Mice",
            "description": "Wireless office keyboard",
            "price": 1799,
            "stock": 35,
        },
        {
            "name": "Wireless Mouse",
            "category": "Keyboards & Mice",
            "description": "Office wireless mouse",
            "price": 999,
            "stock": 45,
        },
        {
            "name": "Bluetooth Headset",
            "category": "Audio",
            "description": "Call center bluetooth headset",
            "price": 3499,
            "stock": 27,
        },
        {
            "name": "Laptop Pro 14",
            "category": "Laptops",
            "description": "Business productivity laptop",
            "price": 49999,
            "stock": 12,
        },
    ]
    prompts = []
    monkeypatch.setattr(tools, "get_products", lambda db: wireless_products)
    monkeypatch.setattr(
        tools,
        "ask_llm",
        lambda prompt: prompts.append(prompt) or "Wireless products",
    )

    answer = tools.generate_product_lookup(
        None, "What are the wireless devices/products available?"
    )

    assert answer == "Wireless products"
    assert len(prompts) == 1
    for product_name in (
        "Wireless Earbuds",
        "Bluetooth Speaker",
        "Wireless Keyboard",
        "Wireless Mouse",
        "Bluetooth Headset",
    ):
        assert product_name in prompts[0]
    for irrelevant_product in (
        "Gaming Mouse",
        "Laptop Backpack",
        "Laptop Pro 14",
    ):
        assert irrelevant_product not in prompts[0]


def test_recommendations_use_same_wireless_shortlist(monkeypatch):
    wireless_products = [
        {
            "name": "Wireless Earbuds",
            "category": "Audio",
            "description": "Bluetooth earbuds with noise cancellation",
            "price": 2499,
            "stock": 40,
        },
        {
            "name": "Bluetooth Speaker",
            "category": "Audio",
            "description": "Portable bluetooth speaker",
            "price": 2999,
            "stock": 20,
        },
        {
            "name": "Gaming Mouse",
            "category": "Gaming Accessories",
            "description": "RGB gaming mouse",
            "price": 1499,
            "stock": 50,
        },
        {
            "name": "Wireless Keyboard",
            "category": "Keyboards & Mice",
            "description": "Wireless office keyboard",
            "price": 1799,
            "stock": 35,
        },
    ]
    prompts = []
    monkeypatch.setattr(tools, "get_products", lambda db: wireless_products)
    monkeypatch.setattr(
        tools,
        "ask_llm",
        lambda prompt: prompts.append(prompt) or "Recommendation",
    )

    answer = tools.generate_product_recommendation(
        None, "Recommend wireless products."
    )

    assert answer == "Recommendation"
    assert len(prompts) == 1
    assert "Wireless Earbuds" in prompts[0]
    assert "Bluetooth Speaker" in prompts[0]
    assert "Wireless Keyboard" in prompts[0]
    assert "Gaming Mouse" not in prompts[0]
