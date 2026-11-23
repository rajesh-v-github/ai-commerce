import json
import re
from decimal import Decimal

from app.models.order import Order
from app.models.ticket import Ticket
from app.models.user import User
from app.models.ticket_message import TicketMessage
from app.models.ticket_status_history import TicketStatusHistory
from app.services.ollama_service import ask_llm
from app.models.product import Product


def generate_executive_summary(db, ticket_id):
    summary = get_ticket_summary(db, ticket_id)

    if not summary:
        return None

    ticket = summary["ticket"]

    conversation = []

    for msg in summary["messages"][-5:]:
        conversation.append(
            f"{msg.user.username} " f"({msg.user.role}): " f"{msg.message}"
        )

    conversation_text = "\n".join(conversation)

    recommendation = recommend_next_action(db, ticket_id)

    prompt = f"""
        You are assisting a customer service executive.

        Create a concise executive summary.

        IMPORTANT:
        - Return plain text only.
        - Do not use markdown.
        - Do not use ** characters.
        - Do not use bullet points.
        - Keep the summary under 150 words.

        Include:
        1. Issue Summary
        2. Current Status
        3. Key Customer Concern
        4. Recommended Next Action

        Analyze the ticket and return ONLY valid JSON.

        Output format:

        {{
            "issue_summary": "",
            "current_status": "",
            "key_customer_concern": "",
            "recommended_next_action": ""
        }}

        Ticket Subject:
        {ticket.subject}

        Ticket Status:
        {ticket.status}

        Conversation:
        {conversation_text}

        Recommended Action:
        {recommendation['recommended_action']}

        Rules:
        - Return JSON only.
        - No markdown.
        - No explanation.
        - No code blocks.
        """

    ai_summary = ask_llm(prompt)

    ai_summary = ai_summary.strip().strip('"')

    try:
        parsed = json.loads(ai_summary)
    except Exception:
        parsed = {
            "issue_summary": "",
            "current_status": "",
            "key_customer_concern": "",
            "recommended_next_action": recommendation["recommended_action"],
        }

    return {
        "ticket_id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "subject": ticket.subject,
        "status": ticket.status,
        "priority": recommendation["priority"],
        "issue_summary": parsed["issue_summary"],
        "current_status": parsed["current_status"],
        "key_customer_concern": parsed["key_customer_concern"],
        "recommended_next_action": parsed["recommended_next_action"],
    }


def recommend_next_action(db, ticket_id):
    summary = get_ticket_summary(db, ticket_id)

    if not summary:
        return None

    ticket = summary["ticket"]

    messages = summary["messages"]

    latest_text = ""

    if messages:
        latest_text = messages[-1].message.lower()

    action = ""
    priority = "LOW"
    urgent_words = ["waiting", "update", "status", "delay", "problem", "issue"]

    escalation_words = ["unhappy", "frustrated", "escalate", "not resolved", "angry"]

    if any(word in latest_text for word in urgent_words):
        action = "Provide a progress update and communicate expected timelines."
        priority = "HIGH"

    elif any(word in latest_text for word in escalation_words):
        action = "Escalate the issue and contact the customer proactively."
        priority = "CRITICAL"

    elif (
        "thank you" in latest_text
        or "resolved" in latest_text
        or "works now" in latest_text
    ):
        action = "Confirm resolution and close the ticket."
        priority = "LOW"

    elif ticket.status == "OPEN":
        action = "Review the ticket and gather missing information."
        priority = "MEDIUM"

    elif ticket.status == "IN_PROGRESS":
        action = "Continue investigation and provide updates."
        priority = "MEDIUM"

    elif ticket.status == "RESOLVED":
        action = "Verify customer satisfaction before closure."
        priority = "LOW"

    elif ticket.status == "CLOSED":
        action = "No action required."
        priority = "LOW"

    return {
        "ticket_id": ticket.id,
        "subject": ticket.subject,
        "status": ticket.status,
        "priority": priority,
        "recommended_action": action,
    }


def generate_draft_response(db, ticket_id):
    summary = get_ticket_summary(db, ticket_id)

    if not summary:
        return None

    ticket = summary["ticket"]

    conversation = []

    for msg in summary["messages"][-5:]:
        conversation.append(f"{msg.user.username} ({msg.user.role}): {msg.message}")

    conversation_text = "\n".join(conversation)

    status_guidance = ""

    if ticket.status == "RESOLVED":
        status_guidance = (
            "The ticket is resolved. The response should confirm resolution "
            "and ask the customer if any additional help is needed."
        )

    elif ticket.status == "IN_PROGRESS":
        status_guidance = (
            "The investigation is still ongoing. Provide an update without "
            "claiming the issue is resolved."
        )

    elif ticket.status == "OPEN":
        status_guidance = "The issue has been received and is awaiting investigation."

    prompt = f"""
        You are assisting a customer service executive.
        Your task is to draft a response TO the customer.

        IMPORTANT RULES:

        - Write as a support representative.
        - The response must be addressed TO the customer.
        - Do not write as the customer.
        - Use only the information provided below.
        - Do not invent shipment information.
        - Do not invent tracking numbers.
        - Do not invent delivery dates.
        - Do not invent order status.
        - Do not assume facts not explicitly provided.
        - If information is unavailable, state that it is unavailable.
        - Return only the response body.
        - Do not explain your reasoning.
        - Do not include greetings such as:
        "Here is a draft response"

        CRITICAL:

        You must not introduce facts that are not explicitly present
        in the ticket status or conversation.

        Examples of prohibited assumptions:
        - "logistics team checked"
        - "shipment dispatched"
        - "tracking number sent"
        - "delivery in 24 hours"
        - "refund processed"

        Return only the response message.

        Do not start with:
        - TO the customer
        - Dear Customer
        - Response:
        - Draft Response:

        Return only the message body.

        If specific information is unavailable,
        simply acknowledge the ticket status.

        Ticket Subject:
        {ticket.subject}

        Ticket Status:
        {ticket.status}

        Recent Conversation:
        {conversation_text}

        Additional Guidance:
        {status_guidance}

        Generate a professional response that a support representative can send to the customer.
        """

    ai_response = ask_llm(prompt)
    ai_response = ai_response.strip().strip('"')

    return {
        "subject": ticket.subject,
        "status": ticket.status,
        "ai_response": ai_response,
    }


def get_ticket_summary(db, ticket_id):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        return None

    messages = (
        db.query(TicketMessage)
        .filter(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.id.asc())
        .all()
    )

    history = (
        db.query(TicketStatusHistory)
        .filter(TicketStatusHistory.ticket_id == ticket_id)
        .order_by(TicketStatusHistory.id.asc())
        .all()
    )

    return {"ticket": ticket, "messages": messages, "history": history}


def get_customer_summary(db, customer_id):
    order_count = db.query(Order).filter(Order.customer_id == customer_id).count()

    ticket_count = db.query(Ticket).filter(Ticket.user_id == customer_id).count()

    latest_ticket = (
        db.query(Ticket)
        .filter(Ticket.user_id == customer_id)
        .order_by(Ticket.id.desc())
        .first()
    )

    return {
        "orders": order_count,
        "tickets": ticket_count,
        "latest_ticket": latest_ticket,
    }


def get_latest_order(db, customer_id):
    return (
        db.query(Order)
        .filter(Order.customer_id == customer_id)
        .order_by(Order.id.desc())
        .first()
    )


def get_open_tickets(db, customer_id):
    return db.query(Ticket).filter(Ticket.user_id == customer_id).all()


def get_customer_360(db, customer_id):
    customer = db.query(User).filter(User.id == customer_id).first()

    if not customer:
        return None

    latest_order = (
        db.query(Order)
        .filter(Order.customer_id == customer_id)
        .order_by(Order.id.desc())
        .first()
    )

    tickets = db.query(Ticket).filter(Ticket.user_id == customer_id).all()

    open_tickets = [t for t in tickets if t.status in ["OPEN", "IN_PROGRESS"]]

    return {
        "customer_id": customer.id,
        "username": customer.username,
        "role": customer.role,
        "total_orders": (
            db.query(Order).filter(Order.customer_id == customer_id).count()
        ),
        "latest_order": (
            {
                "order_number": latest_order.order_number,
                "status": latest_order.status,
                "total_amount": latest_order.total_amount,
            }
            if latest_order
            else None
        ),
        "total_tickets": len(tickets),
        "open_tickets": len(
            [t for t in tickets if t.status in ["OPEN", "IN_PROGRESS"]]
        ),
    }


def generate_ai_insights(db, ticket_id):

    summary = get_ticket_summary(db, ticket_id)

    if not summary:
        return None

    ticket = summary["ticket"]

    conversation = []

    for msg in summary["messages"][-5:]:
        conversation.append(
            f"{msg.user.username} " f"({msg.user.role}): " f"{msg.message}"
        )

    conversation_text = "\n".join(conversation)

    recommendation = recommend_next_action(db, ticket_id)

    prompt = f"""
    You are a customer support copilot.

    Analyze the ticket information below.

    Ticket Subject:
    {ticket.subject}

    Ticket Status:
    {ticket.status}

    Conversation:
    {conversation_text}

    Recommended Action:
    {recommendation["recommended_action"]}

    Return ONLY valid JSON.

    {{
    "executive_summary": {{
        "issue_summary": "brief one sentence summary",
        "current_status": "OPEN or IN_PROGRESS or RESOLVED or CLOSED",
        "key_customer_concern": "main concern expressed by customer",
        "recommended_next_action": "recommended next action"
    }},
    "draft_response": "professional customer response"
    }}

    Rules:

    - Fill every field.
    - Do not leave any field blank.
    - Use actual ticket information.
    - Return valid JSON only.
    - No markdown.
    - No code blocks.
    - No explanation.
    """
    ai_response = ask_llm(prompt)

    cleaned = ai_response.replace("\n", " ").replace("\r", " ")

    ai_response = cleaned.strip().strip('"')

    print("\n========== RAW OLLAMA RESPONSE ==========")
    print(ai_response)
    print("=========================================\n")

    try:
        parsed = json.loads(ai_response.strip())
        exec_summary = parsed.get("executive_summary", {})

        if not exec_summary.get("issue_summary"):
            exec_summary["issue_summary"] = ticket.subject

        if not exec_summary.get("current_status"):
            exec_summary["current_status"] = ticket.status

        if not exec_summary.get("key_customer_concern"):
            exec_summary["key_customer_concern"] = "Customer requested an update."

        if not exec_summary.get("recommended_next_action"):
            exec_summary["recommended_next_action"] = recommendation[
                "recommended_action"
            ]

        parsed["executive_summary"] = exec_summary
        print("\n========== PARSED JSON ==========")
        print(parsed)
        print("=================================\n")

        return parsed

    except Exception as ex:

        print(f"AI parsing failed: {ex}")

        return {
            "executive_summary": {
                "issue_summary": "",
                "current_status": ticket.status,
                "key_customer_concern": "",
                "recommended_next_action": recommendation["recommended_action"],
            },
            "draft_response": "",
        }


def generate_copilot_answer(
    customer,
    orders,
    tickets,
    ticket_summary,
    question,
):

    ticket = ticket_summary["ticket"]

    conversation = []

    for msg in ticket_summary["messages"][-5:]:

        conversation.append(f"{msg.user.username}: " f"{msg.message}")

    conversation_text = "\n".join(conversation)

    prompt = f"""
        You are a customer support copilot.

        IMPORTANT:

        - Use ONLY the information below.
        - Do NOT invent causes.
        - Do NOT invent payment issues.
        - Do NOT invent shipment information.
        - Do NOT invent tracking numbers.
        - If the information is unavailable,
        say:
        "The available ticket information
        does not contain that detail."

        Customer:
        Username: {customer["username"]}

        Orders Count:
        {customer["total_orders"]}

        Open Tickets:
        {customer["open_tickets"]}

        Ticket Subject:
        {ticket.subject}

        Ticket Status:
        {ticket.status}

        Conversation:
        {conversation_text}

        Question:
        {question}

        Answer in plain English.
        Return only the answer.
        """

    return ask_llm(prompt)


def get_customer_orders(db, customer_id):
    return (
        db.query(Order)
        .filter(Order.customer_id == customer_id)
        .order_by(Order.id.desc())
        .all()
    )


def _get_order_status_filter(question, orders):
    explicit_status = re.search(
        r"\bstatus\s*(?:=|:|\bis\b)\s*[\"']?([a-z][a-z0-9_-]*)",
        question,
        re.IGNORECASE,
    )
    if explicit_status:
        status_value = explicit_status.group(1).strip()
        if status_value.casefold() not in {
            "least",
            "most",
            "common",
            "frequent",
            "the",
            "all",
            "each",
            "every",
            "breakdown",
            "distribution",
            "summary",
            "count",
            "counts",
        }:
            return status_value

    known_statuses = {
        order.status.strip()
        for order in orders
        if order.status and order.status.strip()
    }
    return next(
        (
            status
            for status in sorted(known_statuses, key=len, reverse=True)
            if re.search(rf"(?<!\w){re.escape(status)}(?!\w)", question, re.I)
        ),
        None,
    )


def _get_order_metric(question):
    if re.search(
        r"\b(?:most common|most frequent)\s+(?:order\s+)?status\b|"
        r"\b(?:order\s+)?status\b.{0,30}\b(?:most common|most frequent)\b|"
        r"\bstatus\s+(?:with|has)\s+(?:the\s+)?most\s+orders?\b",
        question,
        re.IGNORECASE,
    ):
        return "most_common_status"
    if re.search(
        r"\b(?:least common|least frequent)\s+(?:order\s+)?status\b|"
        r"\b(?:order\s+)?status\b.{0,30}\b(?:least common|least frequent)\b|"
        r"\bstatus\s+(?:with|has)\s+(?:the\s+)?fewest\s+orders?\b",
        question,
        re.IGNORECASE,
    ):
        return "least_common_status"
    if re.search(
        r"\b(status\s+(?:breakdown|distribution|summary|counts?)|"
        r"orders?\s+by\s+status|status\s+of\s+(?:all\s+)?orders|"
        r"(?:each|every|per|by)\s+status|"
        r"(?:count|number)\s+of\s+orders?\s+by\s+status)\b|"
        r"\bhow many orders?.{0,30}(?:each|every|per)\s+status\b",
        question,
        re.IGNORECASE,
    ):
        return "status_breakdown"
    if re.search(
        r"\b(?:most|top|highest|best)\b.{0,25}"
        r"\b(?:ordered|purchased|quantity|units?)\b|"
        r"\b(?:ordered|purchased)\b.{0,25}\b(?:most|top|highest)\b|"
        r"\b(?:most|top)\s+popular\s+products?\b",
        question,
        re.IGNORECASE,
    ):
        return "top_product"
    if re.search(
        r"\baverage\b.{0,25}\b(?:items?|units?|quantities)\b|"
        r"\b(?:items?|units?)\b.{0,25}\baverage\b",
        question,
        re.IGNORECASE,
    ):
        return "average_item_quantity"
    if re.search(
        r"\b(?:how many|total|sum|number of)\b.{0,30}"
        r"\b(?:items?|units?|quantities)\b",
        question,
        re.IGNORECASE,
    ):
        return "item_quantity"
    if re.search(
        r"\b(?:highest|largest|greatest|maximum|max|biggest|most expensive)\b",
        question,
        re.IGNORECASE,
    ) and re.search(
        r"\b(?:amount|total|value|order|orders|expensive|cost|spend|revenue|sales)\b",
        question,
        re.IGNORECASE,
    ):
        return "highest_amount"
    if re.search(
        r"\b(?:lowest|smallest|minimum|min|least expensive|cheapest)\b",
        question,
        re.IGNORECASE,
    ) and re.search(
        r"\b(?:amount|total|value|order|orders|expensive|cost|spend|revenue|sales)\b",
        question,
        re.IGNORECASE,
    ):
        return "lowest_amount"
    if re.search(r"\b(?:average|avg|mean)\b", question, re.IGNORECASE) and re.search(
        r"\b(?:amount|value|order|orders|spend|revenue|sales)\b",
        question,
        re.IGNORECASE,
    ):
        return "average_amount"
    if re.search(
        r"\b(?:how many|number of|count|total number of)\b.{0,35}\borders?\b|"
        r"\borders?\b.{0,25}\b(?:count|number)\b",
        question,
        re.IGNORECASE,
    ):
        return "order_count"
    if re.search(
        r"\b(?:total|sum|spent|spend|how much)\b.{0,35}"
        r"\b(?:amount|value|order|orders|money|spend|spent|revenue|sales)\b|"
        r"\b(?:amount|value|money|revenue|sales)\b.{0,25}\b(?:total|sum|spent|spend)\b",
        question,
        re.IGNORECASE,
    ):
        return "total_amount"
    return None


def get_customer_tickets(db, customer_id):
    return (
        db.query(Ticket)
        .filter(Ticket.user_id == customer_id)
        .order_by(Ticket.id.desc())
        .all()
    )


def get_products(db):

    products = db.query(Product).all()

    return [
        {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "stock": product.stock,
            "description": product.description,
            "category": product.category,
        }
        for product in products
    ]


PRODUCT_QUERY_STOP_WORDS = {
    "a",
    "all",
    "an",
    "and",
    "are",
    "available",
    "about",
    "affordable",
    "best",
    "at",
    "below",
    "budget",
    "can",
    "cheap",
    "cheapest",
    "customer",
    "details",
    "device",
    "devices",
    "do",
    "expensive",
    "for",
    "give",
    "good",
    "highest",
    "how",
    "high",
    "higher",
    "lowest",
    "lower",
    "in",
    "information",
    "is",
    "item",
    "items",
    "k",
    "least",
    "less",
    "least",
    "expensive",
    "priced",
    "list",
    "looking",
    "look",
    "lowest",
    "maximum",
    "match",
    "matching",
    "gb",
    "tb",
    "inch",
    "inches",
    "hz",
    "mah",
    "cm",
    "mm",
    "me",
    "more",
    "most",
    "max",
    "minimum",
    "maximum",
    "premium",
    "need",
    "no",
    "of",
    "on",
    "option",
    "options",
    "or",
    "particularly",
    "please",
    "price",
    "purchase",
    "purchases",
    "purchasable",
    "buy",
    "bought",
    "product",
    "products",
    "recommend",
    "recommendation",
    "recommendations",
    "related",
    "search",
    "show",
    "stock",
    "suggest",
    "suitable",
    "valuable",
    "than",
    "the",
    "to",
    "under",
    "up",
    "want",
    "what",
    "where",
    "which",
    "within",
    "with",
    "would",
    "you",
}
PRODUCT_TYPE_TERMS = {
    "backpack",
    "bag",
    "case",
    "earbud",
    "headphone",
    "headset",
    "hub",
    "keyboard",
    "laptop",
    "monitor",
    "mouse",
    "speaker",
    "watch",
    "webcam",
}
PRODUCT_TERM_GROUPS = (
    {"bluetooth", "cordless", "wireless"},
    {"laptop", "notebook"},
    {"earbud", "earphone"},
    {"headphone", "headset"},
    {"monitor", "display"},
)
PRODUCT_ACCESSORY_TERMS = {
    "accessory",
    "adapter",
    "bag",
    "backpack",
    "cable",
    "case",
    "charger",
    "hub",
}
PRODUCT_PLURAL_TERMS = {
    "accessories": "accessory",
    "bags": "bag",
    "cases": "case",
    "devices": "device",
    "displays": "display",
    "earbuds": "earbud",
    "earphones": "earphone",
    "headphones": "headphone",
    "headsets": "headset",
    "hubs": "hub",
    "keyboards": "keyboard",
    "laptops": "laptop",
    "monitors": "monitor",
    "mice": "mouse",
    "notebooks": "notebook",
    "products": "product",
    "speakers": "speaker",
    "watches": "watch",
    "webcams": "webcam",
}


def _normalize_product_terms(text):
    return {
        PRODUCT_PLURAL_TERMS.get(term, term)
        for term in re.findall(r"[a-z]+", text.casefold())
    }


def _product_question_terms(question):
    return _normalize_product_terms(question) - PRODUCT_QUERY_STOP_WORDS


def _product_term_matches(term, product_terms):
    if term == "accessory":
        return bool(PRODUCT_ACCESSORY_TERMS & product_terms)
    synonym_group = next(
        (group for group in PRODUCT_TERM_GROUPS if term in group),
        {term},
    )
    return bool(synonym_group & product_terms)


def _filter_relevant_products(products, question, *, recommendation=False):
    terms = _product_question_terms(question)
    if not terms:
        return products

    term_groups = [
        next((group for group in PRODUCT_TERM_GROUPS if term in group), {term})
        for term in terms
    ]
    type_groups = [
        group for term, group in zip(terms, term_groups)
        if term in PRODUCT_TYPE_TERMS
    ]
    accessory_requested = bool(
        {"accessory", "accessories", "add-on", "addons"} & set(
            re.findall(r"[a-z-]+", question.casefold())
        )
    )
    availability_requested = bool(
        re.search(r"\b(?:in stock|available|availability)\b", question, re.I)
    )
    max_price_match = re.search(
        r"\b(?:under|below|less than|up to|no more than|at most|max(?:imum)?(?: budget)?)\s*"
        r"(?:₹|rs\.?\s*)?([\d,]+(?:\.\d+)?\s*[kK]?)",
        question,
        re.IGNORECASE,
    )
    max_price = None
    if max_price_match:
        value = max_price_match.group(1).replace(",", "").strip()
        multiplier = 1000 if value.casefold().endswith("k") else 1
        max_price = float(re.sub(r"[kK]$", "", value)) * multiplier

    relevant = []
    for product in products:
        name_category_terms = _normalize_product_terms(
            f"{product['name']} {product.get('category') or ''}"
        )
        all_product_terms = name_category_terms | _normalize_product_terms(
            product.get("description") or ""
        )

        if not all(
            _product_term_matches(term, all_product_terms)
            for term in terms
        ):
            continue
        if any(
            not _product_term_matches(next(iter(group)), name_category_terms)
            for group in type_groups
        ):
            continue

        product_name_terms = _normalize_product_terms(product["name"])
        is_accessory = bool(product_name_terms & PRODUCT_ACCESSORY_TERMS)
        if (
            is_accessory
            and not accessory_requested
            and type_groups
        ):
            continue
        if availability_requested and (product.get("stock") or 0) <= 0:
            continue
        if recommendation and max_price is not None:
            if product.get("price") is None or product["price"] > max_price:
                continue
        relevant.append(product)

    return relevant


def _recommendation_price_order(question):
    if re.search(
        r"\b(?:cheapest|least expensive|lowest priced|lower priced|"
        r"less expensive|less in price|lower in price|more affordable|"
        r"price\s+low(?:est)?\s+to\s+high)\b",
        question,
        re.IGNORECASE,
    ):
        return "ascending"
    if re.search(
        r"\b(?:most expensive|highest priced|higher priced|"
        r"more expensive|higher in price|price\s+high(?:est)?\s+to\s+low)\b",
        question,
        re.IGNORECASE,
    ):
        return "descending"
    return None


def _order_recommendation_products(products, question):
    unique_products = []
    seen_names = set()
    for product in products:
        normalized_name = product["name"].strip().casefold()
        if normalized_name not in seen_names:
            unique_products.append(product)
            seen_names.add(normalized_name)

    price_order = _recommendation_price_order(question)
    if price_order == "ascending":
        return sorted(
            unique_products,
            key=lambda product: (
                product.get("price") is None,
                product.get("price") if product.get("price") is not None else 0,
                product["name"].casefold(),
            ),
        )
    if price_order == "descending":
        return sorted(
            unique_products,
            key=lambda product: (
                product.get("price") is None,
                -(product.get("price") or 0),
                product["name"].casefold(),
            ),
        )
    return unique_products


def _format_recommendation_answer(answer, products):
    cleaned_answer = answer.replace("```json", "").replace("```", "").strip()
    recommendations = None

    try:
        parsed_answer = json.loads(cleaned_answer)
    except json.JSONDecodeError:
        parsed_answer = None

    if isinstance(parsed_answer, dict):
        recommendations = parsed_answer.get("recommendations")
    elif isinstance(parsed_answer, list):
        recommendations = parsed_answer

    if isinstance(recommendations, list) and not recommendations:
        return "No products in the catalog match those requirements."

    product_by_name = {
        product["name"].strip().casefold(): product for product in products
    }
    selected = {}
    if isinstance(recommendations, list):
        for item in recommendations:
            if isinstance(item, str):
                name = item.strip()
                reason = ""
            elif isinstance(item, dict):
                name = str(
                    item.get("product") or item.get("name") or ""
                ).strip()
                reason = str(item.get("reason") or "").strip()
            else:
                continue
            product = product_by_name.get(name.casefold())
            if product:
                selected.setdefault(product["name"].casefold(), (product, reason))
    else:
        for product in products:
            product_name_pattern = re.compile(
                rf"(?<![\w]){re.escape(product['name'])}(?![\w])",
                re.IGNORECASE,
            )
            if product_name_pattern.search(cleaned_answer):
                selected.setdefault(
                    product["name"].casefold(),
                    (product, product.get("description") or ""),
                )

    if not selected:
        return cleaned_answer

    formatted = []
    for product in products:
        selected_product = selected.get(product["name"].casefold())
        if not selected_product:
            continue
        _, reason = selected_product
        formatted.append(
            f"Product: {product['name']}\n"
            f"Category: {product.get('category') or 'Not specified'}\n"
            f"Price: ₹{product['price']}\n"
            f"Stock: {product['stock']}\n"
            f"Description: {product.get('description') or 'Not specified'}\n"
            f"Reason: {reason or product.get('description') or 'Matches the stated requirements.'}"
        )

    return "\n\n".join(formatted)


def generate_product_lookup(db, question):

    products = _filter_relevant_products(get_products(db), question)
    if not products:
        return "No matching products were found in the catalog."

    product_text = "\n".join(
        [
            f"Product: {p['name']}\n"
            f"Category: {p['category'] or 'Not specified'}\n"
            f"Price: ₹{p['price']}\n"
            f"Stock: {p['stock']}\n"
            f"Description: {p['description'] or 'Not specified'}"
            for p in products
        ]
    )

    prompt = f"""
        You are a retail product assistant.

        Relevance-Matched Catalog Products:
        {product_text}

        Question:
        {question}

        Relevance review:
        1. The backend has shortlisted the catalog entries relevant to the question.
           Treat this list as the complete allowed result set.
        2. Carefully check the question against each shortlisted product's exact name,
           category, and relevant description. Return only matching products; never
           add products from outside this list or the full catalog.
        3. Interpret common equivalent terms consistently (for example, wireless and
           Bluetooth; laptop and notebook), but do not treat unrelated accessories
           as a match for the primary product type.
        4. Do not return the full catalog just because the question uses a broad term.

        Output rules:
        - Use only the available product catalog data; never invent product details.
        - Return only products that pass the relevance review; do not pad results.
        - For each product, use this exact plain-text layout:
          Product: [exact product name]
          Category: [catalog category or Not specified]
          Price: [price]
          Stock: [stock]
          Description: [brief description]
        - Separate products with a blank line.
        - Do not use bullets, numbering, markdown, code blocks, or decorative separators.
        - If no products match, say that no matching products were found.
        - Keep the response concise and professional.

        Answer the support executive's question.
        """

    answer = ask_llm(prompt)

    answer = answer.replace("```json", "").replace("```", "").strip()

    return answer


def generate_product_recommendation(db, question):

    products = _order_recommendation_products(
        _filter_relevant_products(
            get_products(db), question, recommendation=True
        ),
        question,
    )
    if not products:
        return "No products in the catalog match those requirements."

    product_text = "\n".join(
        [
            f"Product: {p['name']}\n"
            f"Category: {p['category'] or 'Not specified'}\n"
            f"Description: {p['description'] or 'Not specified'}\n"
            f"Price: ₹{p['price']}\n"
            f"Stock: {p['stock']}"
            for p in products
        ]
    )

    prompt = f"""
        You are a retail product recommendation assistant.

        Relevance-Matched Catalog Products:
        {product_text}

        Customer Requirement:
        {question}

        Relevance review:
        1. The backend has shortlisted the catalog entries relevant to the stated
           requirement. Treat this list as the complete allowed recommendation set.
        2. Carefully compare the requirement's product-type/category keywords,
           required features, use case, budget, and availability with the listed
           catalog data.
        3. Recommend only listed products that satisfy the requested product type
           and every stated constraint. Do not add a product from the wider catalog.
        4. Compare actual product names and categories, using descriptions to verify
           features; do not broaden a product-type match to unrelated accessories.
        5. Interpret common equivalents consistently (for example, wireless and
           Bluetooth; laptop and notebook), without treating unrelated items as
           equivalent products.
        6. If no listed product clearly qualifies, say so instead of broadening the
           request.
        7. If the requirement asks for a lower, lowest, cheaper, or least expensive
           option, recommend in ascending price order (lowest first). If it asks for
           a higher or most expensive option, use descending price order.
        8. Recommend each exact catalog product at most once. Never duplicate a
           product under a different recommendation number or heading.

        Output rules:
        - Use only exact products and facts from the catalog; do not invent details.
        - If only one product qualifies, return only that product.
        - Give a brief, factual reason each recommendation matches the requirement.
        - Return only valid JSON with this shape:
          {{"recommendations":[{{"product":"exact catalog product name","reason":"brief factual match"}}]}}
        - Include each recommended product once. Return an empty recommendations
          array if no product qualifies. Do not include markdown or code fences.

        Provide recommendations.
        """

    answer = ask_llm(prompt)

    return _format_recommendation_answer(answer, products)


def generate_order_lookup(db, customer_id, question):
    orders = get_customer_orders(db, customer_id)

    if not orders:
        return "No orders were found for this customer."

    requested_status = _get_order_status_filter(question, orders)
    if requested_status:
        orders = [
            order
            for order in orders
            if (order.status or "").strip().casefold()
            == requested_status.casefold()
        ]

    if not orders:
        return f"No orders were found with status {requested_status.upper()}."

    metric = _get_order_metric(question)
    if metric in {"status_breakdown", "most_common_status", "least_common_status"}:
        status_counts = {}
        for order in orders:
            status = (order.status or "UNKNOWN").strip().upper()
            status_counts[status] = status_counts.get(status, 0) + 1
        if metric in {"most_common_status", "least_common_status"}:
            target_count = (
                max(status_counts.values())
                if metric == "most_common_status"
                else min(status_counts.values())
            )
            matching_statuses = sorted(
                status
                for status, count in status_counts.items()
                if count == target_count
            )
            label = (
                "Most common status"
                if metric == "most_common_status"
                else "Least common status"
            )
            order_label = "order" if target_count == 1 else "orders"
            return (
                f"{label}: {', '.join(matching_statuses)} "
                f"({target_count} {order_label})."
            )
        breakdown = "\n".join(
            f"{status}: {count}"
            for status, count in sorted(status_counts.items())
        )
        return f"Order status breakdown ({len(orders)} orders):\n{breakdown}"

    if metric == "order_count":
        order_label = "order" if len(orders) == 1 else "orders"
        return f"Found {len(orders)} {order_label}."

    if metric in {"item_quantity", "average_item_quantity", "top_product"}:
        order_items = [
            item
            for order in orders
            for item in (order.items or [])
        ]
        if not order_items:
            return "No order item data is available for this customer."

        if metric == "item_quantity":
            total_quantity = sum(item.quantity or 0 for item in order_items)
            unit_label = "unit" if total_quantity == 1 else "units"
            return (
                f"Total items ordered: {total_quantity} {unit_label} "
                f"across {len(orders)} orders."
            )

        if metric == "average_item_quantity":
            average_quantity = (
                sum(item.quantity or 0 for item in order_items) / len(orders)
            )
            order_label = "order" if len(orders) == 1 else "orders"
            return (
                f"Average items per order: {average_quantity:.2f} units "
                f"across {len(orders)} {order_label}."
            )

        product_quantities = {}
        product_names = {}
        for item in order_items:
            product_key = (
                item.product_id
                if item.product_id is not None
                else item.product_name
            )
            if product_key is None:
                continue
            product_quantities[product_key] = (
                product_quantities.get(product_key, 0) + (item.quantity or 0)
            )
            product_names[product_key] = item.product_name or str(product_key)
        if not product_quantities:
            return "No order item data is available for this customer."
        highest_quantity = max(product_quantities.values())
        top_products = sorted(
            (
                product_names[key],
                quantity,
            )
            for key, quantity in product_quantities.items()
            if quantity == highest_quantity
        )
        product_lines = "\n".join(
            f"{name}: {quantity} {'unit' if quantity == 1 else 'units'}"
            for name, quantity in top_products
        )
        return f"Most ordered product(s):\n{product_lines}"

    order_amounts = [
        (order, Decimal(str(order.total_amount)))
        for order in orders
        if order.total_amount is not None
    ]
    if metric in {"highest_amount", "lowest_amount"}:
        if not order_amounts:
            return "No order amount data is available for this customer."
        target_amount = (
            max(amount for _, amount in order_amounts)
            if metric == "highest_amount"
            else min(amount for _, amount in order_amounts)
        )
        matching_orders = [
            (order, amount)
            for order, amount in order_amounts
            if amount == target_amount
        ]
        label = "Highest" if metric == "highest_amount" else "Lowest"
        order_lines = [
            f"Order {index}: {order.order_number}\n"
            f"Status: {order.status}\n"
            f"Amount: ₹{amount:,.2f}"
            for index, (order, amount) in enumerate(matching_orders, start=1)
        ]
        return f"{label} order amount: ₹{target_amount:,.2f}\n\n" + "\n\n".join(
            order_lines
        )

    if metric in {"average_amount", "total_amount"}:
        if not order_amounts:
            return "No order amount data is available for this customer."
        amount_total = sum(
            (amount for _, amount in order_amounts), Decimal("0")
        )
        if metric == "average_amount":
            average = amount_total / len(order_amounts)
            return (
                f"Average order amount: ₹{average:,.2f} "
                f"across {len(order_amounts)} orders."
            )
        return (
            f"Total order amount: ₹{amount_total:,.2f} "
            f"across {len(order_amounts)} orders."
        )

    if requested_status:
        order_lines = [
            f"Order {index}: {order.order_number}\n"
            f"Status: {order.status}\n"
            f"Amount: ₹{order.total_amount}"
            for index, order in enumerate(orders, start=1)
        ]
        return (
            f"Found {len(orders)} orders with status "
            f"{requested_status.upper()}.\n\n"
            + "\n\n".join(order_lines)
        )

    order_text = "\n".join([f"""
            Order Number: {order.order_number}
            Status: {order.status}
            Amount: ₹{order.total_amount}
            """ for order in orders])

    prompt = f"""
            You are an order support assistant.

            Relevant Customer Orders:
            {order_text}

            Question:

            {question}

            IMPORTANT:

            - Use only the available order data.
            - Do not invent order statuses.
            - Do not invent delivery dates.
            - Do not invent tracking information.
            - Answer in plain English.
            - Keep the response concise.
            - When returning multiple orders, number only the order headings
              (for example, "Order 1: ORD-001", "Order 2: ORD-002").
            - Put order details on separate labeled lines, such as
              "Status: PROCESSING" and "Amount: ₹1234.00".
            - Never number or bullet order details.
            - Never use separator lines such as "====", "----", or "****".
            - Do not wrap the response in Markdown code blocks or decorative formatting.
            - If returning one order, use an unnumbered heading
              (for example, "Order: ORD-001").
            - If the question asks for the highest, largest, or most expensive order,
              return only the order(s) listed with the highest amount.
            - Include only orders relevant to the question.
            """

    answer = ask_llm(prompt)

    return answer.replace("```", "").strip()


def generate_ticket_details(question):

    prompt = f"""
            You are a customer support assistant.
            Extract ticket information.
            Return ONLY valid JSON.

            Format:
            {{
                "subject": "",
                "description": "",
                "priority": ""
            }}

            Priority must be one of:
            LOW
            MEDIUM
            HIGH
            CRITICAL

            Customer Statement:
            {question}
            """

    response = ask_llm(prompt)

    response = response.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(response)

    except Exception:
        return {
            "subject": "General Support Request",
            "description": question,
            "priority": "MEDIUM",
        }
