from decimal import Decimal
from types import SimpleNamespace

import pytest

import app.agents.tools as tools


@pytest.fixture
def orders():
    return [
        SimpleNamespace(
            order_number="ORD-LOW",
            status="DELIVERED",
            total_amount=Decimal("20.00"),
            items=[
                SimpleNamespace(product_id=1, product_name="Widget", quantity=2),
                SimpleNamespace(product_id=2, product_name="Cable", quantity=1),
            ],
        ),
        SimpleNamespace(
            order_number="ORD-HIGH",
            status="PROCESSING",
            total_amount=Decimal("75.50"),
            items=[
                SimpleNamespace(product_id=1, product_name="Widget", quantity=3)
            ],
        ),
        SimpleNamespace(
            order_number="ORD-MID",
            status="DELIVERED",
            total_amount=Decimal("40.00"),
            items=[
                SimpleNamespace(product_id=3, product_name="Adapter", quantity=4)
            ],
        ),
    ]


@pytest.fixture
def mock_order_lookup(monkeypatch, orders):
    monkeypatch.setattr(tools, "get_customer_orders", lambda db, customer_id: orders)
    monkeypatch.setattr(
        tools,
        "ask_llm",
        lambda prompt: pytest.fail("Metric queries should not require Ollama"),
    )


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Which order has the highest amount?", "ORD-HIGH"),
        ("Which order has the lowest amount?", "ORD-LOW"),
        ("What is the average order amount?", "₹45.17"),
        ("What is the total amount spent?", "₹135.50"),
        ("How many orders has this customer placed?", "Found 3 orders."),
        ("How many delivered orders?", "Found 2 orders."),
        ("How many items were ordered in total?", "Total items ordered: 10 units"),
        ("What is the average number of items per order?", "3.33 units"),
        ("What product was ordered the most?", "Widget: 5 units"),
    ],
)
def test_order_metrics(question, expected, mock_order_lookup):
    answer = tools.generate_order_lookup(None, 10, question)

    assert expected in answer


def test_status_breakdown(mock_order_lookup):
    answer = tools.generate_order_lookup(None, 10, "Show the order status breakdown.")

    assert "Order status breakdown (3 orders)" in answer
    assert "DELIVERED: 2" in answer
    assert "PROCESSING: 1" in answer


def test_status_breakdown_per_status_phrase(mock_order_lookup):
    answer = tools.generate_order_lookup(None, 10, "How many orders are there per status?")

    assert "DELIVERED: 2" in answer
    assert "PROCESSING: 1" in answer


def test_most_common_status_returns_breakdown(mock_order_lookup):
    answer = tools.generate_order_lookup(None, 10, "Which status has the most orders?")

    assert answer == "Most common status: DELIVERED (2 orders)."


def test_least_common_status(mock_order_lookup):
    answer = tools.generate_order_lookup(None, 10, "Which order status is least common?")

    assert answer == "Least common status: PROCESSING (1 order)."


def test_amount_average_can_be_scoped_by_status(mock_order_lookup):
    answer = tools.generate_order_lookup(
        None, 10, "What is the average amount for delivered orders?"
    )

    assert "Average order amount: ₹30.00 across 2 orders." == answer


def test_explicit_unknown_status_returns_no_matches(mock_order_lookup):
    answer = tools.generate_order_lookup(
        None, 10, "Show orders where status = CANCELLED."
    )

    assert answer == "No orders were found with status CANCELLED."


def test_unrecognized_question_still_uses_ollama(monkeypatch, orders):
    monkeypatch.setattr(tools, "get_customer_orders", lambda db, customer_id: orders)
    prompts = []
    monkeypatch.setattr(
        tools,
        "ask_llm",
        lambda prompt: prompts.append(prompt) or "Ollama response",
    )

    answer = tools.generate_order_lookup(None, 10, "Tell me about this customer's orders.")

    assert answer == "Ollama response"
    assert len(prompts) == 1
    assert "Tell me about this customer's orders." in prompts[0]
