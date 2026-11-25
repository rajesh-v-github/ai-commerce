import json
import re
from decimal import Decimal

import httpx

from app.models.order import Order
from app.models.product import Product
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.models.ticket_status_history import TicketStatusHistory
from app.models.user import User
from app.services.ollama_service import AIServiceUnavailableError, ask_llm

LLM_UNAVAILABLE_ERRORS = (
    ConnectionError,
    OSError,
    TimeoutError,
    AIServiceUnavailableError,
    httpx.HTTPError,
)

WORD_NUMBER_MAP = {
    "one": 1,
    "single": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _extract_json_object(raw_text: str):
    if not raw_text:
        return None
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _fallback_executive_summary_fields(ticket, messages, recommended_action: str) -> dict:
    customer_messages = [
        m.message.strip()
        for m in (messages or [])
        if getattr(m, "user", None)
        and getattr(m.user, "role", "") == "customer"
        and (m.message or "").strip()
    ]
    issue_summary = (
        f"{ticket.subject} — {ticket.description.strip()}"
        if getattr(ticket, "description", None) and ticket.description.strip()
        else ticket.subject
    )
    status_descriptions = {
        "OPEN": "OPEN — Received and awaiting support review.",
        "IN_PROGRESS": "IN_PROGRESS — Active investigation underway by support.",
        "RESOLVED": "RESOLVED — Resolution shared; awaiting final customer confirmation.",
        "CLOSED": "CLOSED — Ticket closed with no pending actions.",
    }
    status_key = (ticket.status or "OPEN").upper()
    return {
        "issue_summary": issue_summary,
        "current_status": status_descriptions.get(status_key, ticket.status or "OPEN"),
        "key_customer_concern": (
            customer_messages[-1]
            if customer_messages
            else (getattr(ticket, "description", None) or ticket.subject)
        ),
        "recommended_next_action": recommended_action,
    }


def _fallback_draft_response_text(ticket) -> str:
    ticket_ref = getattr(ticket, "ticket_number", None) or f"Ticket #{ticket.id}"
    status_key = (ticket.status or "OPEN").upper()
    if status_key == "RESOLVED":
        return (
            f"Thank you for reaching out regarding '{ticket.subject}' ({ticket_ref}). "
            "Our records indicate that this ticket is currently marked as RESOLVED. "
            "Please let us know if everything is working as expected or if you need any additional assistance."
        )
    if status_key == "IN_PROGRESS":
        return (
            f"Thank you for contacting us regarding '{ticket.subject}' ({ticket_ref}). "
            "Your request is currently IN_PROGRESS and under active investigation by our support team. "
            "Specific resolution details are not yet available, and we will follow up with an update as soon as our review is complete."
        )
    if status_key == "OPEN":
        return (
            f"Thank you for contacting support regarding '{ticket.subject}' ({ticket_ref}). "
            "We have received your request and your ticket is currently OPEN awaiting investigation. "
            "Please share any relevant order number or additional context if available, and we will update you shortly."
        )
    return (
        f"Thank you for reaching out regarding '{ticket.subject}' ({ticket_ref}). "
        f"This ticket is currently marked as {status_key}. Please reply if you require further assistance."
    )


def _sanitize_draft_response(raw_response: str, conversation_text: str, ticket) -> str:
    cleaned = (raw_response or "").replace("```", "").replace("**", "").strip().strip('"')
    cleaned = re.sub(
        r"^(?:here(?:'s| is)\s+(?:a|the|your)\s+[^:\n]*:\s*|"
        r"(?:draft\s+)?response\s*:\s*|"
        r"to\s+the\s+customer\s*:\s*|"
        r"subject\s*:[^\n]*\n+)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(
        r"^(?:dear\s+[^,\n]+,\s*)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # Guard against common small-model hallucinations not grounded in conversation
    source_blob = f"{getattr(ticket, 'subject', '')} {getattr(ticket, 'description', '')} {conversation_text}".lower()
    hallucination_patterns = [
        (r"\btracking\s+number\b", "tracking"),
        (r"\brefund\s+(?:has\s+been\s+)?processed\b", "refund processed"),
        (r"\bdelivered\s+within\s+\d+\s+hours\b", "hours"),
    ]
    for pattern, required_keyword in hallucination_patterns:
        if re.search(pattern, cleaned, re.IGNORECASE) and required_keyword not in source_blob:
            return _fallback_draft_response_text(ticket)

    return cleaned


def generate_executive_summary(db, ticket_id):
    summary = get_ticket_summary(db, ticket_id)
    if not summary:
        return None

    ticket = summary["ticket"]
    conversation = [
        f"{msg.user.username} ({msg.user.role}): {msg.message}"
        for msg in summary["messages"][-6:]
    ]
    conversation_text = "\n".join(conversation) or "No conversation messages recorded yet."
    ticket_desc = (getattr(ticket, "description", None) or "").strip() or "Not provided"
    recommendation = recommend_next_action(db, ticket_id)

    prompt = f"""You are assisting a customer service executive.

Analyze the support ticket below step by step and produce a concise executive summary grounded strictly in the provided ticket facts.

Ticket Number: {getattr(ticket, 'ticket_number', None) or ticket.id}
Ticket Subject: {ticket.subject}
Ticket Description: {ticket_desc}
Ticket Status: {ticket.status}
Conversation:
{conversation_text}

Baseline Recommended Action:
{recommendation['recommended_action']}

Rules:
- First write a brief internal verification in "analysis", then populate the four summary fields.
- Keep plain-text values concise (under 150 words total across fields), without markdown, **, or bullet points.
- Never invent shipment, tracking, payment, or resolution facts not stated above.
- Return ONLY valid JSON with this exact structure:
{{
  "analysis": "1-sentence verification of ticket state and customer concern",
  "issue_summary": "concise factual summary of the reported issue",
  "current_status": "current ticket status and operational state",
  "key_customer_concern": "primary concern expressed by the customer",
  "recommended_next_action": "concrete next step for the support executive"
}}"""

    fallback_fields = _fallback_executive_summary_fields(
        ticket, summary["messages"], recommendation["recommended_action"]
    )
    try:
        ai_summary = ask_llm(prompt)
        parsed = _extract_json_object(ai_summary) or {}
    except LLM_UNAVAILABLE_ERRORS:
        parsed = fallback_fields
    except Exception:
        parsed = fallback_fields

    return {
        "ticket_id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "subject": ticket.subject,
        "status": ticket.status,
        "priority": recommendation["priority"],
        "issue_summary": (parsed.get("issue_summary") or fallback_fields["issue_summary"]).replace("**", "").strip(),
        "current_status": (parsed.get("current_status") or fallback_fields["current_status"]).replace("**", "").strip(),
        "key_customer_concern": (
            parsed.get("key_customer_concern") or fallback_fields["key_customer_concern"]
        ).replace("**", "").strip(),
        "recommended_next_action": (
            parsed.get("recommended_next_action") or fallback_fields["recommended_next_action"]
        ).replace("**", "").strip(),
    }


def recommend_next_action(db, ticket_id):
    summary = get_ticket_summary(db, ticket_id)
    if not summary:
        return None

    ticket = summary["ticket"]
    messages = summary["messages"]
    latest_text = messages[-1].message.lower() if messages else (getattr(ticket, "description", "") or "").lower()

    action = ""
    priority = "LOW"
    urgent_words = ["waiting", "update", "status", "delay", "problem", "issue"]
    escalation_words = ["unhappy", "frustrated", "escalate", "not resolved", "angry"]

    if any(word in latest_text for word in escalation_words):
        action = "Escalate the issue and contact the customer proactively."
        priority = "CRITICAL"
    elif any(word in latest_text for word in urgent_words):
        action = "Provide a progress update and communicate expected timelines."
        priority = "HIGH"
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
    conversation = [
        f"{msg.user.username} ({msg.user.role}): {msg.message}"
        for msg in summary["messages"][-6:]
    ]
    conversation_text = "\n".join(conversation) or "No prior messages recorded."
    ticket_desc = (getattr(ticket, "description", None) or "").strip() or "Not specified"

    status_guidance = ""
    if ticket.status == "RESOLVED":
        status_guidance = (
            "The ticket is RESOLVED. Confirm the resolution clearly and ask the customer "
            "if anything else is needed before closing."
        )
    elif ticket.status == "IN_PROGRESS":
        status_guidance = (
            "The investigation is still IN_PROGRESS. Reassure the customer with an honest "
            "status update without claiming the issue is already resolved."
        )
    elif ticket.status == "OPEN":
        status_guidance = (
            "The ticket is OPEN and awaiting investigation. Acknowledge receipt empathetically "
            "and request any missing details only if needed."
        )
    elif ticket.status == "CLOSED":
        status_guidance = "The ticket is CLOSED. Politely acknowledge and invite the customer to reach out if new questions arise."

    prompt = f"""You are a senior customer support representative drafting a direct reply TO the customer.

Ticket Reference: {getattr(ticket, 'ticket_number', None) or ticket.id}
Ticket Subject: {ticket.subject}
Ticket Description: {ticket_desc}
Current Ticket Status: {ticket.status}
Recent Conversation:
{conversation_text}

Operational Guidance:
{status_guidance}

STRICT GROUNDING & OUTPUT RULES:
- Write directly TO the customer as a helpful, empathetic support specialist (2 to 4 sentences).
- Use ONLY facts explicitly present in the Ticket Subject, Description, Status, and Conversation above.
- NEVER invent tracking numbers, courier names, delivery dates, refund completions, or internal team actions that are not stated above.
- Do NOT include greetings like "Dear Customer,", headers like "Draft Response:" or "Subject:", markdown, or quotation marks.
- Return ONLY the plain-text reply body."""

    try:
        raw_response = ask_llm(prompt)
        ai_response = _sanitize_draft_response(raw_response, conversation_text, ticket)
    except LLM_UNAVAILABLE_ERRORS:
        ai_response = _fallback_draft_response_text(ticket)

    if not ai_response:
        ai_response = _fallback_draft_response_text(ticket)

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

    return {
        "customer_id": customer.id,
        "username": customer.username,
        "role": customer.role,
        "total_orders": db.query(Order).filter(Order.customer_id == customer_id).count(),
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
        "open_tickets": len([t for t in tickets if t.status in ["OPEN", "IN_PROGRESS"]]),
    }


def generate_ai_insights(db, ticket_id):
    summary = get_ticket_summary(db, ticket_id)
    if not summary:
        return None

    ticket = summary["ticket"]
    conversation = [
        f"{msg.user.username} ({msg.user.role}): {msg.message}"
        for msg in summary["messages"][-6:]
    ]
    conversation_text = "\n".join(conversation) or "No conversation messages recorded yet."
    ticket_desc = (getattr(ticket, "description", None) or "").strip() or "Not provided"
    recommendation = recommend_next_action(db, ticket_id)

    prompt = f"""You are a senior customer support copilot.

Analyze the ticket details below and produce an executive summary plus a customer-ready draft reply.

Ticket Subject: {ticket.subject}
Ticket Description: {ticket_desc}
Ticket Status: {ticket.status}
Conversation:
{conversation_text}

Recommended Action:
{recommendation["recommended_action"]}

Return ONLY valid JSON with this exact structure:
{{
  "analysis": "brief step-by-step verification of ticket status, customer concern, and safe reply scope",
  "executive_summary": {{
    "issue_summary": "brief one-sentence factual summary",
    "current_status": "OPEN or IN_PROGRESS or RESOLVED or CLOSED",
    "key_customer_concern": "main concern expressed by customer",
    "recommended_next_action": "recommended next action"
  }},
  "draft_response": "empathetic plain-text response addressed to the customer without invented tracking or delivery claims"
}}

Rules:
- Populate every field using only verified ticket data.
- Never invent shipment, tracking, or payment facts.
- Return ONLY valid JSON without markdown or code fences."""

    fallback_exec = _fallback_executive_summary_fields(
        ticket, summary["messages"], recommendation["recommended_action"]
    )
    fallback_draft = _fallback_draft_response_text(ticket)

    try:
        ai_response = ask_llm(prompt)
        parsed = _extract_json_object(ai_response) or {}
        exec_summary = parsed.get("executive_summary") or {}

        if not exec_summary.get("issue_summary"):
            exec_summary["issue_summary"] = fallback_exec["issue_summary"]
        if not exec_summary.get("current_status"):
            exec_summary["current_status"] = fallback_exec["current_status"]
        if not exec_summary.get("key_customer_concern"):
            exec_summary["key_customer_concern"] = fallback_exec["key_customer_concern"]
        if not exec_summary.get("recommended_next_action"):
            exec_summary["recommended_next_action"] = recommendation["recommended_action"]

        parsed["executive_summary"] = exec_summary
        raw_draft = parsed.get("draft_response") or ""
        cleaned_draft = _sanitize_draft_response(raw_draft, conversation_text, ticket)
        parsed["draft_response"] = cleaned_draft or fallback_draft
        return parsed

    except LLM_UNAVAILABLE_ERRORS:
        return {
            "executive_summary": fallback_exec,
            "draft_response": fallback_draft,
        }
    except Exception as ex:
        print(f"AI parsing failed: {ex}")
        return {
            "executive_summary": fallback_exec,
            "draft_response": fallback_draft,
        }


def generate_copilot_answer(
    customer,
    orders,
    tickets,
    ticket_summary,
    question,
):
    ticket = ticket_summary["ticket"]
    conversation = [
        f"{msg.user.username}: {msg.message}"
        for msg in ticket_summary["messages"][-6:]
    ]
    conversation_text = "\n".join(conversation) or "No messages yet."
    ticket_desc = (getattr(ticket, "description", None) or "").strip() or "Not specified"

    recent_orders_lines = []
    for idx, ord_obj in enumerate((orders or [])[:5], start=1):
        rank_note = " (LATEST)" if idx == 1 else ""
        recent_orders_lines.append(
            f"{idx}. {ord_obj.order_number}{rank_note} — Status: {ord_obj.status}, Amount: ₹{ord_obj.total_amount}"
        )
    orders_context = "\n".join(recent_orders_lines) or "No orders on file."

    prompt = f"""You are a senior customer support copilot answering an executive's question.

Verified Customer & Ticket Context:
- Customer Username: {customer["username"]}
- Total Orders: {customer["total_orders"]}
- Open Tickets: {customer["open_tickets"]}
- Recent Orders (Newest First):
{orders_context}
- Active Ticket: {getattr(ticket, 'ticket_number', None) or ticket.id} — {ticket.subject} (Status: {ticket.status})
- Ticket Description: {ticket_desc}
- Conversation:
{conversation_text}

Executive Question:
{question}

STRICT RULES:
- Answer concisely in plain English using ONLY the verified context above.
- Do NOT invent causes, payment issues, shipment dates, or tracking numbers.
- If the requested detail is not present in the context above, say: "The available ticket information does not contain that detail."
- Return only the answer."""

    try:
        return ask_llm(prompt)
    except LLM_UNAVAILABLE_ERRORS:
        return (
            f"Ticket {ticket.ticket_number or ticket.id} ('{ticket.subject}') for "
            f"{customer['username']} is currently {ticket.status}. "
            f"Customer has {customer['total_orders']} total order(s) and "
            f"{customer['open_tickets']} open ticket(s)."
        )


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
        r"(?:each|every|per)\s+status|"
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
        r"\borders?\s+count\b",
        question,
        re.IGNORECASE,
    ) and not re.search(r"\border\s+numbers?\b", question, re.IGNORECASE):
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


def _parse_money_token(raw_token: str) -> Decimal:
    cleaned = raw_token.replace(",", "").strip()
    multiplier = Decimal("1000") if cleaned.casefold().endswith("k") else Decimal("1")
    numeric = re.sub(r"[kK]$", "", cleaned)
    return Decimal(numeric) * multiplier


def _extract_requested_order_count(question: str) -> int | None:
    q = question or ""
    explicit_phrase = re.search(
        r"\b(?:only|just|top|last|latest|recent|newest|first|oldest|earliest)\s+"
        r"(one|single|two|three|four|five|six|seven|eight|nine|ten|\d+)\b",
        q,
        re.IGNORECASE,
    )
    if explicit_phrase:
        tok = explicit_phrase.group(1).casefold()
        val = WORD_NUMBER_MAP.get(tok) if not tok.isdigit() else int(tok)
        if val and val > 0:
            return val

    leading_num = re.search(
        r"\b(one|single|two|three|four|five|\d+)\s+(?:[\w/-]+\s+){0,3}orders?\b",
        q,
        re.IGNORECASE,
    )
    if leading_num:
        tok = leading_num.group(1).casefold()
        val = WORD_NUMBER_MAP.get(tok) if not tok.isdigit() else int(tok)
        if val and val > 0:
            return val

    return None


def _plan_order_selection(orders: list, question: str):
    """Pre-analyze customer orders (sorted newest-first) against chronological, ID, and amount constraints."""
    q = (question or "").strip()
    q_lower = q.casefold()

    # 1. Explicit full order numbers (e.g. ORD-20261125-0031, ORD-017)
    explicit_ord = re.findall(r"\bord-[a-z0-9-]+\b", q_lower)
    if explicit_ord:
        wanted = {code.upper() for code in explicit_ord}
        matched = [
            o for o in orders if (getattr(o, "order_number", "") or "").upper() in wanted
        ]
        if not matched:
            return (
                [],
                True,
                f"No matching order ({', '.join(sorted(wanted))}) was found for this customer.",
            )
        return (
            matched,
            True,
            f"Matched explicit order number(s): {', '.join(o.order_number for o in matched)}.",
        )

    # 2. Shorthand serial lookup (e.g. "order 017", "order #31")
    shorthand_nums = re.findall(r"\border\s*#?\s*0*(\d{1,4})\b", q_lower)
    if shorthand_nums and not re.search(
        r"\b(?:last|latest|first|oldest|top|recent)\s+order\b", q_lower
    ):
        matched = []
        for o in orders:
            ord_num = (getattr(o, "order_number", "") or "").upper()
            if any(
                re.search(rf"(?:^|-)0*{re.escape(serial)}$", ord_num)
                for serial in shorthand_nums
            ):
                matched.append(o)
        if not matched:
            return (
                [],
                True,
                f"No order matching #{', #'.join(shorthand_nums)} was found for this customer.",
            )
        return (
            matched,
            True,
            f"Matched requested order serial(s): {', '.join(o.order_number for o in matched)}.",
        )

    candidate_orders = list(orders)
    narrowed = False
    notes = []

    # 3. Amount range / threshold filters on orders
    between_match = re.search(
        r"\bbetween\s*(?:₹|rs\.?\s*)?([\d,]+(?:\.\d+)?\s*[kK]?)\s*(?:and|to|-)\s*(?:₹|rs\.?\s*)?([\d,]+(?:\.\d+)?\s*[kK]?)",
        q,
        re.IGNORECASE,
    )
    if between_match:
        low_amt = _parse_money_token(between_match.group(1))
        high_amt = _parse_money_token(between_match.group(2))
        if low_amt > high_amt:
            low_amt, high_amt = high_amt, low_amt
        candidate_orders = [
            o
            for o in candidate_orders
            if o.total_amount is not None
            and low_amt <= Decimal(str(o.total_amount)) <= high_amt
        ]
        narrowed = True
        notes.append(f"Filtered to orders between ₹{low_amt:,.2f} and ₹{high_amt:,.2f}.")
    else:
        max_amt_match = re.search(
            r"\b(?:under|below|less than|up to|at most)\s*(?:₹|rs\.?\s*)?([\d,]+(?:\.\d+)?\s*[kK]?)",
            q,
            re.IGNORECASE,
        )
        min_amt_match = re.search(
            r"\b(?:above|over|more than|greater than|at least)\s*(?:₹|rs\.?\s*)?([\d,]+(?:\.\d+)?\s*[kK]?)",
            q,
            re.IGNORECASE,
        )
        if max_amt_match:
            cap = _parse_money_token(max_amt_match.group(1))
            candidate_orders = [
                o
                for o in candidate_orders
                if o.total_amount is not None and Decimal(str(o.total_amount)) <= cap
            ]
            narrowed = True
            notes.append(f"Filtered to orders up to ₹{cap:,.2f}.")
        if min_amt_match:
            floor = _parse_money_token(min_amt_match.group(1))
            candidate_orders = [
                o
                for o in candidate_orders
                if o.total_amount is not None and Decimal(str(o.total_amount)) >= floor
            ]
            narrowed = True
            notes.append(f"Filtered to orders of at least ₹{floor:,.2f}.")

    if narrowed and not candidate_orders:
        return ([], True, "No orders for this customer match that amount criteria.")

    # 4. Chronological rank & count limit ("only one last/latest order", "oldest order", "last 2 orders")
    if re.search(r"\b(?:second|2nd)\s+(?:last|latest|most\s+recent)\b|\bprevious\s+order\b", q_lower):
        chosen = [candidate_orders[1]] if len(candidate_orders) >= 2 else candidate_orders[:1]
        return (chosen, True, "Selected the customer's second most recent (previous) order.")

    requested_count = _extract_requested_order_count(q)
    singular_order_word = bool(re.search(r"\border\b", q_lower)) and not bool(
        re.search(r"\borders\b", q_lower)
    )
    has_latest = bool(
        re.search(r"\b(?:latest|last|most\s+recent|newest|recent|current)\b", q_lower)
    )
    has_oldest = bool(re.search(r"\b(?:oldest|earliest|first)\b", q_lower))

    if has_latest and not has_oldest:
        limit = requested_count or (1 if singular_order_word else None)
        if limit is not None:
            selected = candidate_orders[:limit]
            notes.append(
                f"Customer orders are sorted newest-first; selected the {len(selected)} most recent/latest order(s) "
                f"(Latest order is {selected[0].order_number} out of {len(orders)} total orders)."
            )
            return (selected, True, " ".join(notes))

    if has_oldest and not has_latest:
        limit = requested_count or (1 if singular_order_word else None)
        if limit is not None:
            selected = list(reversed(candidate_orders[-limit:]))
            notes.append(
                f"Selected the {len(selected)} oldest/earliest order(s) "
                f"(Earliest order is {selected[0].order_number} out of {len(orders)} total orders)."
            )
            return (selected, True, " ".join(notes))

    if requested_count is not None:
        selected = candidate_orders[:requested_count]
        notes.append(f"Selected {len(selected)} order(s) (most recent first).")
        return (selected, True, " ".join(notes))

    return (candidate_orders, narrowed, " ".join(notes))


def _format_order_cards(target_orders: list, intro: str = "") -> str:
    blocks = []
    single = len(target_orders) == 1
    for idx, o in enumerate(target_orders, start=1):
        heading = f"Order: {o.order_number}" if single else f"Order {idx}: {o.order_number}"
        amt = Decimal(str(o.total_amount if o.total_amount is not None else 0))
        lines = [
            heading,
            f"Status: {o.status}",
            f"Amount: ₹{amt:,.2f}",
        ]
        created_at = getattr(o, "created_at", None)
        if created_at is not None:
            date_str = (
                created_at.strftime("%Y-%m-%d %H:%M")
                if hasattr(created_at, "strftime")
                else str(created_at)[:16]
            )
            if date_str.strip():
                lines.append(f"Order Date: {date_str}")

        payment_method = getattr(o, "payment_method", None)
        payment_status = getattr(o, "payment_status", None)
        if payment_method:
            pay_label = f"{payment_method} ({payment_status})" if payment_status else str(payment_method)
            lines.append(f"Payment: {pay_label}")

        item_summary = ", ".join(
            f"{it.product_name} (x{it.quantity})"
            for it in (getattr(o, "items", None) or [])
            if getattr(it, "product_name", None)
        )
        if item_summary:
            lines.append(f"Items: {item_summary}")

        blocks.append("\n".join(lines))

    cards_text = "\n\n".join(blocks)
    clean_intro = (intro or "").replace("**", "").strip()
    if clean_intro:
        return f"{clean_intro}\n\n{cards_text}"
    return cards_text


def _sanitize_order_summary(summary: str, allowed_orders: list, all_orders: list) -> str:
    if not summary or not isinstance(summary, str):
        return ""
    cleaned = summary.replace("```", "").replace("**", "").strip()
    if not cleaned:
        return ""

    allowed_codes = {(o.order_number or "").upper() for o in allowed_orders}
    all_codes = {(o.order_number or "").upper() for o in all_orders}
    mentioned_codes = {m.upper() for m in re.findall(r"\bord-[a-z0-9-]+\b", cleaned, re.IGNORECASE)}

    # Reject summary if it mentions an excluded customer order (e.g. ORD-017 when ORD-20261125-0031 is selected)
    # or an invented order code
    if any(code not in allowed_codes for code in mentioned_codes):
        return ""
    for o in all_orders:
        code = (o.order_number or "").upper()
        if code and code not in allowed_codes and code in cleaned.upper():
            return ""
    # Also reject if summary contradicts actual order status for single-order queries
    if len(allowed_orders) == 1:
        actual_status = (allowed_orders[0].status or "").upper()
        other_statuses = {"DELIVERED", "SHIPPED", "PROCESSING", "CONFIRMED", "CANCELLED"} - {actual_status}
        if any(re.search(rf"\b{st}\b", cleaned, re.IGNORECASE) for st in other_statuses):
            return ""
    _ = all_codes
    return cleaned


def get_customer_tickets(db, customer_id):
    return (
        db.query(Ticket)
        .filter(Ticket.user_id == customer_id)
        .order_by(Ticket.id.desc())
        .all()
    )


def get_products(db):
    products = (
        db.query(Product)
        .filter((Product.is_active.is_(None)) | (Product.is_active.is_(True)))
        .all()
    )

    return [
        {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "stock": product.stock,
            "description": product.description,
            "category": product.category,
            "brand": getattr(product, "brand", None),
            "sku": getattr(product, "sku", None),
            "specifications": getattr(product, "specifications", None),
            "target_audience": getattr(product, "target_audience", None),
        }
        for product in products
    ]


PRODUCT_QUERY_STOP_WORDS = {
    "a", "about", "above", "affordable", "all", "also", "an", "and", "any", "are",
    "as", "associated", "at", "availability", "available", "based", "below", "best",
    "between", "bought", "bring", "budget", "buy", "by", "called", "can", "catalog",
    "catalogue", "categories", "category", "cheap", "cheapest", "check", "cm",
    "concerning", "cost", "costing", "current", "currently", "customer", "customers",
    "detail", "details", "device", "devices", "displaying", "do", "does", "each",
    "every", "expensive", "fetch", "find", "for", "from", "gb", "gear", "get", "give",
    "good", "got", "greater", "has", "have", "help", "here", "high", "higher",
    "highest", "how", "hz", "i", "in", "inch", "inches", "info", "information", "into",
    "inventory", "is", "it", "item", "items", "just", "k", "kind", "kinds", "least",
    "less", "like", "list", "listing", "look", "looking", "low", "lower", "lowest",
    "mah", "match", "matches", "matching", "max", "maximum", "me", "min", "minimum",
    "mm", "more", "most", "my", "named", "need", "needs", "no", "now", "of", "offer",
    "offered", "on", "one", "only", "option", "options", "or", "our", "out", "over",
    "particularly", "please", "premium", "price", "priced", "product", "products",
    "provide", "purchasable", "purchase", "purchases", "range", "recommend",
    "recommendation", "recommendations", "regarding", "relate", "related", "relating",
    "return", "right", "rs", "search", "see", "selection", "sell", "selling", "sells",
    "share", "shop", "show", "showing", "similar", "single", "sold", "some", "sort",
    "sorts", "stock", "stocked", "store", "such", "suggest", "suitable", "tb", "tell",
    "than", "that", "the", "their", "them", "there", "these", "they", "this", "those",
    "to", "top", "type", "types", "unavailable", "under", "up", "us", "valuable",
    "view", "want", "wants", "we", "what", "where", "which", "with", "within", "would",
    "you", "your",
}

PRODUCT_TYPE_TERMS = {
    "adapter", "backpack", "bag", "battery", "camera", "case", "charger", "display",
    "dock", "earbud", "earphone", "headphone", "headset", "hub", "keyboard", "laptop",
    "luggage", "monitor", "mouse", "notebook", "pouch", "powerbank", "screen",
    "sleeve", "smartwatch", "speaker", "watch", "wearable", "webcam",
}

PRODUCT_TERM_GROUPS = (
    {"bluetooth", "cordless", "wireless"},
    {"laptop", "notebook"},
    {"earbud", "earphone", "tws"},
    {"headphone", "headset"},
    {"monitor", "display", "screen"},
    {"bag", "backpack", "case", "sleeve", "pouch", "luggage", "carry", "carrying"},
    {"webcam", "camera"},
    {"watch", "smartwatch", "wearable"},
    {"powerbank", "battery", "charger", "charging"},
    {"hub", "dock", "docking", "multiport", "adapter"},
    {"conference", "conferencing", "meeting"},
    {"fitness", "tracker", "tracking", "sport"},
)

PRODUCT_ACCESSORY_TERMS = {
    "accessory", "adapter", "backpack", "bag", "cable", "carry", "carrying", "case",
    "charger", "dock", "docking", "hub", "luggage", "multiport", "pouch", "sleeve",
}

IRREGULAR_PRODUCT_TERMS = {
    "accessories": "accessory", "adapters": "adapter", "backpacks": "backpack",
    "bags": "bag", "batteries": "battery", "cables": "cable", "cameras": "camera",
    "cases": "case", "chargers": "charger", "computers": "computer",
    "devices": "device", "displays": "display", "docks": "dock", "earbuds": "earbud",
    "earphones": "earphone", "headphones": "headphone", "headsets": "headset",
    "hubs": "hub", "keyboards": "keyboard", "laptops": "laptop", "mice": "mouse",
    "monitors": "monitor", "notebooks": "notebook", "peripherals": "peripheral",
    "pouches": "pouch", "powerbanks": "powerbank", "products": "product",
    "screens": "screen", "sleeves": "sleeve", "smartwatches": "smartwatch",
    "speakers": "speaker", "stands": "stand", "switches": "switch",
    "trackers": "tracker", "watches": "watch", "wearables": "wearable",
    "webcams": "webcam",
}

NON_PLURAL_S_WORDS = {
    "business", "chassis", "cordless", "fitness", "focus", "glass", "ips", "less",
    "plus", "series", "status", "tws", "wireless",
}


def _normalize_single_product_word(word: str) -> str:
    w = word.casefold()
    if w in IRREGULAR_PRODUCT_TERMS:
        return IRREGULAR_PRODUCT_TERMS[w]
    if w in NON_PLURAL_S_WORDS or len(w) <= 3:
        return w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("ches", "shes", "xes", "zes")) and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and not w.endswith(("ss", "us", "is", "os")):
        return w[:-1]
    return w


def _normalize_product_terms(text):
    raw_words = re.findall(r"[a-z]+", (text or "").casefold())
    normalized = {_normalize_single_product_word(w) for w in raw_words}

    # Unify 1-word and 2-word hardware compounds ("Smart Watch" <-> "smartwatch", "Power Bank" <-> "powerbank")
    if "smartwatch" in normalized:
        normalized.add("watch")
    elif "smart" in normalized and "watch" in normalized:
        normalized.add("smartwatch")

    if "powerbank" in normalized:
        normalized.update({"power", "bank"})
    elif "power" in normalized and "bank" in normalized:
        normalized.add("powerbank")

    return normalized


def _get_synonym_group(term: str) -> set[str]:
    return next(
        (group for group in PRODUCT_TERM_GROUPS if term in group),
        {term},
    )


def _product_question_terms(question):
    scrubbed = re.sub(
        r"\b(?:out\s+of\s+stock|in\s+stock|sold\s+out|list\s+out)\b",
        " ",
        question or "",
        flags=re.IGNORECASE,
    )
    scrubbed = re.sub(
        r"\bbetween\s*(?:₹|rs\.?\s*)?[\d,]+(?:\.\d+)?\s*[kK]?\s*(?:and|to|-)\s*(?:₹|rs\.?\s*)?[\d,]+(?:\.\d+)?\s*[kK]?",
        " ",
        scrubbed,
        flags=re.IGNORECASE,
    )
    scrubbed = re.sub(
        r"\b(?:under|below|less than|up to|no more than|at most|max(?:imum)?(?: budget)?|"
        r"above|over|more than|greater than|at least|min(?:imum)?(?: budget)?)\s*"
        r"(?:₹|rs\.?\s*)?[\d,]+(?:\.\d+)?\s*[kK]?",
        " ",
        scrubbed,
        flags=re.IGNORECASE,
    )
    terms = _normalize_product_terms(scrubbed) - PRODUCT_QUERY_STOP_WORDS
    # Remove standalone "power" & "bank" when combined into "powerbank" so "powerbank" acts as one unified concept
    if "powerbank" in terms:
        terms.discard("power")
        terms.discard("bank")
    if "smartwatch" in terms:
        terms.discard("smart")
    return terms


def _product_term_matches(term, product_terms):
    if term == "accessory":
        return bool(PRODUCT_ACCESSORY_TERMS & product_terms)
    return bool(_get_synonym_group(term) & product_terms)


def _extract_price_bounds(question: str) -> tuple[float | None, float | None]:
    q = question or ""
    between_match = re.search(
        r"\bbetween\s*(?:₹|rs\.?\s*)?([\d,]+(?:\.\d+)?\s*[kK]?)\s*(?:and|to|-)\s*(?:₹|rs\.?\s*)?([\d,]+(?:\.\d+)?\s*[kK]?)",
        q,
        re.IGNORECASE,
    )
    if between_match:
        low = float(_parse_money_token(between_match.group(1)))
        high = float(_parse_money_token(between_match.group(2)))
        return (min(low, high), max(low, high))

    min_price = None
    max_price = None

    max_match = re.search(
        r"\b(?:under|below|less than|up to|no more than|at most|max(?:imum)?(?: budget)?)\s*"
        r"(?:₹|rs\.?\s*)?([\d,]+(?:\.\d+)?\s*[kK]?)",
        q,
        re.IGNORECASE,
    )
    if max_match:
        max_price = float(_parse_money_token(max_match.group(1)))

    min_match = re.search(
        r"\b(?:above|over|more than|greater than|at least|min(?:imum)?(?: budget)?)\s*"
        r"(?:₹|rs\.?\s*)?([\d,]+(?:\.\d+)?\s*[kK]?)",
        q,
        re.IGNORECASE,
    )
    if min_match:
        min_price = float(_parse_money_token(min_match.group(1)))

    return (min_price, max_price)


def _filter_relevant_products(products, question, *, recommendation=False):
    _ = recommendation
    out_of_stock_requested = bool(
        re.search(r"\b(?:out\s+of\s+stock|sold\s+out|unavailable)\b", question, re.I)
    )
    availability_requested = not out_of_stock_requested and bool(
        re.search(r"\b(?:in\s+stock|available|availability)\b", question, re.I)
    )
    min_price, max_price = _extract_price_bounds(question)

    terms = _product_question_terms(question)
    if not terms:
        filtered = list(products)
        if out_of_stock_requested:
            filtered = [p for p in filtered if (p.get("stock") or 0) <= 0]
        elif availability_requested:
            filtered = [p for p in filtered if (p.get("stock") or 0) > 0]
        if min_price is not None:
            filtered = [
                p for p in filtered if p.get("price") is not None and p["price"] >= min_price
            ]
        if max_price is not None:
            filtered = [
                p for p in filtered if p.get("price") is not None and p["price"] <= max_price
            ]
        return filtered

    # Deduplicate synonym groups so e.g. "bags or backpacks" forms one unified type group
    unique_type_groups: list[set[str]] = []
    modifier_terms: set[str] = set()
    for term in sorted(terms):
        group = _get_synonym_group(term)
        if term in PRODUCT_TYPE_TERMS or bool(group & PRODUCT_TYPE_TERMS):
            if group not in unique_type_groups:
                unique_type_groups.append(group)
        else:
            modifier_terms.add(term)

    has_disjunctive_connector = bool(
        re.search(r"\b(?:or|and)\b|/|,", question or "", re.IGNORECASE)
    )
    general_accessory_requested = bool(
        {"accessory", "accessories", "add-on", "addons"}
        & set(re.findall(r"[a-z-]+", (question or "").casefold()))
    )

    requested_accessory_terms = terms & PRODUCT_ACCESSORY_TERMS
    expanded_requested_accessories: set[str] = set()
    for acc_term in requested_accessory_terms:
        expanded_requested_accessories |= _get_synonym_group(acc_term)

    # When an accessory is qualified by a host device without "or" (e.g. "laptop bag", "laptop hub"),
    # treat the accessory as the required product type and the host device ("laptop") as a compatibility modifier.
    if (
        expanded_requested_accessories
        and len(unique_type_groups) > 1
        and not re.search(r"\bor\b|/", question or "", re.IGNORECASE)
    ):
        accessory_type_groups = [
            g for g in unique_type_groups if bool(g & PRODUCT_ACCESSORY_TERMS)
        ]
        host_type_groups = [
            g for g in unique_type_groups if not bool(g & PRODUCT_ACCESSORY_TERMS)
        ]
        if accessory_type_groups and host_type_groups:
            unique_type_groups = accessory_type_groups
            for hg in host_type_groups:
                modifier_terms.add(next(iter(hg)))

    relevant = []
    for product in products:
        product_name_terms = _normalize_product_terms(product["name"])
        category_terms = _normalize_product_terms(product.get("category") or "")
        desc_terms = _normalize_product_terms(product.get("description") or "")
        spec_terms = _normalize_product_terms(product.get("specifications") or "")
        audience_terms = _normalize_product_terms(product.get("target_audience") or "")
        brand_terms = _normalize_product_terms(product.get("brand") or "")

        explicit_name_types = product_name_terms & PRODUCT_TYPE_TERMS

        # Prevent compound categories (e.g. "Keyboards & Mice") from bleeding one
        # hardware type ("keyboard") onto a product explicitly named as another ("Wireless Mouse").
        effective_category_terms = (
            category_terms - (PRODUCT_TYPE_TERMS - explicit_name_types)
            if explicit_name_types
            else category_terms
        )
        name_category_terms = product_name_terms | effective_category_terms
        all_product_terms = (
            name_category_terms | desc_terms | spec_terms | audience_terms | brand_terms
        )

        # Check product hardware type groups
        if unique_type_groups:
            def _matches_type_group(group: set[str]) -> bool:
                if explicit_name_types:
                    return bool(group & product_name_terms) or (
                        bool(group & PRODUCT_ACCESSORY_TERMS)
                        and bool(group & category_terms)
                    )
                return bool(group & name_category_terms)

            if len(unique_type_groups) > 1 and has_disjunctive_connector:
                if not any(_matches_type_group(g) for g in unique_type_groups):
                    continue
            else:
                if not all(_matches_type_group(g) for g in unique_type_groups):
                    continue

        # Check modifier / feature / use-case / brand terms
        if modifier_terms:
            if len(modifier_terms) > 1 and re.search(r"\bor\b", question or "", re.I) and not unique_type_groups:
                if not any(_product_term_matches(t, all_product_terms) for t in modifier_terms):
                    continue
            else:
                if not all(_product_term_matches(t, all_product_terms) for t in modifier_terms):
                    continue

        unrequested_accessories = (
            product_name_terms & PRODUCT_ACCESSORY_TERMS
        ) - expanded_requested_accessories
        if (
            unrequested_accessories
            and not general_accessory_requested
            and unique_type_groups
        ):
            continue

        if out_of_stock_requested and (product.get("stock") or 0) > 0:
            continue
        if availability_requested and (product.get("stock") or 0) <= 0:
            continue
        if min_price is not None:
            if product.get("price") is None or product["price"] < min_price:
                continue
        if max_price is not None:
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
        unique_products = sorted(
            unique_products,
            key=lambda product: (
                product.get("price") is None,
                product.get("price") if product.get("price") is not None else 0,
                product["name"].casefold(),
            ),
        )
    elif price_order == "descending":
        unique_products = sorted(
            unique_products,
            key=lambda product: (
                product.get("price") is None,
                -(product.get("price") or 0),
                product["name"].casefold(),
            ),
        )

    explicit_single = bool(
        re.search(r"\b(?:only\s+one|only\s+1|just\s+one|just\s+1|single)\b", question or "", re.I)
    )
    if explicit_single and unique_products:
        return unique_products[:1]

    return unique_products


def _format_lookup_products_list(products):
    return "\n\n".join(
        f"Product: {p['name']}\n"
        f"Category: {p.get('category') or 'Not specified'}\n"
        f"Price: ₹{p['price']}\n"
        f"Stock: {p['stock']}\n"
        f"Description: {p.get('description') or 'Not specified'}"
        for p in products
    )


def _is_exhaustive_list_query(question: str) -> bool:
    return bool(
        re.search(
            r"\b(?:list(?:\s+out)?|give\s+me(?:\s+the|\s+all)?|show(?:\s+me)?(?:\s+all)?|all\s+[\w\s]+available)\b",
            question or "",
            re.IGNORECASE,
        )
    )


def _format_lookup_answer(answer: str, products: list[dict], question: str = "") -> str:
    cleaned_answer = (answer or "").replace("```json", "").replace("```", "").strip()
    if not cleaned_answer:
        return _format_lookup_products_list(products)

    product_by_name = {p["name"].strip().casefold(): p for p in products}

    # Support structured JSON reasoning responses from Ollama
    parsed_json = _extract_json_object(cleaned_answer)
    if isinstance(parsed_json, dict) and isinstance(parsed_json.get("products"), list):
        matched_from_json = []
        seen_json = set()
        for item in parsed_json["products"]:
            raw_name = (
                item.strip()
                if isinstance(item, str)
                else str((item or {}).get("product") or (item or {}).get("name") or "").strip()
                if isinstance(item, dict)
                else ""
            )
            prod = product_by_name.get(raw_name.casefold())
            if prod and prod["name"].casefold() not in seen_json:
                seen_json.add(prod["name"].casefold())
                matched_from_json.append(prod)

        if matched_from_json:
            if _is_exhaustive_list_query(question) and len(products) > len(matched_from_json):
                return _format_lookup_products_list(products)
            return _format_lookup_products_list(matched_from_json)
        if products:
            return _format_lookup_products_list(products)
        return "No matching products were found in the catalog."

    # Plain-text response handling (including unit-test mocks)
    matched = []
    seen = set()
    for product in products:
        pattern = re.compile(
            rf"(?<![\w]){re.escape(product['name'])}(?![\w])",
            re.IGNORECASE,
        )
        if pattern.search(cleaned_answer):
            key = product["name"].casefold()
            if key not in seen:
                seen.add(key)
                matched.append(product)

    if not matched and re.search(
        r"\bno\s+(?:matching\s+)?products?\b", cleaned_answer, re.IGNORECASE
    ):
        return _format_lookup_products_list(products)

    if not matched:
        return cleaned_answer

    if _is_exhaustive_list_query(question):
        return _format_lookup_products_list(products)

    if "Category:" in cleaned_answer or "Price:" in cleaned_answer or len(matched) >= 1:
        return _format_lookup_products_list(matched)

    return cleaned_answer


def _format_recommendation_answer(answer, products, question: str = ""):
    cleaned_answer = (answer or "").replace("```json", "").replace("```", "").strip()
    recommendations = None

    parsed_answer = _extract_json_object(cleaned_answer)
    if isinstance(parsed_answer, dict):
        recommendations = parsed_answer.get("recommendations")
    elif isinstance(parsed_answer, list):
        recommendations = parsed_answer

    if isinstance(recommendations, list) and not recommendations:
        if products:
            recommendations = [
                {
                    "product": p["name"],
                    "reason": p.get("description") or "Matches the stated requirements.",
                }
                for p in products
            ]
        else:
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
                name = str(item.get("product") or item.get("name") or "").strip()
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
        if products and re.search(
            r"\bno\s+(?:matching\s+)?products?\b", cleaned_answer, re.IGNORECASE
        ):
            for p in products:
                selected[p["name"].casefold()] = (
                    p,
                    p.get("description") or "Matches the stated requirements.",
                )
        else:
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
    products = _order_recommendation_products(
        _filter_relevant_products(get_products(db), question),
        question,
    )
    if not products:
        return "No matching products were found in the catalog."

    product_text = "\n\n".join(
        [
            f"Product: {p['name']}\n"
            f"Category: {p.get('category') or 'Not specified'}\n"
            f"Price: ₹{p['price']}\n"
            f"Stock: {p['stock']}\n"
            f"Description: {p.get('description') or 'Not specified'}"
            + (
                f"\nSpecifications: {p['specifications']}"
                if p.get("specifications")
                else ""
            )
            for p in products
        ]
    )

    prompt = f"""You are a retail product assistant.

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
   Bluetooth; laptop and notebook; bag, backpack, and carrying case), while not
   treating unrelated accessories as a match for a primary device type.
4. When a category shares multiple hardware types (such as "Keyboards & Mice"),
   verify the product's own name so a mouse is never returned for a keyboard
   query (and vice versa).
5. Treat conversational phrasing such as "list out", "give me", "give me all",
   or "show available" as a request to include every matching shortlisted product.

Output rules:
- First write a brief 1-sentence verification in "analysis", then list the exact
  matching catalog product names in "products".
- Never invent product names or details.
- Return ONLY valid JSON with this exact shape:
  {{"analysis":"brief step-by-step relevance check","products":["exact catalog product name"]}}"""

    try:
        answer = ask_llm(prompt)
        if answer and answer.strip():
            return _format_lookup_answer(answer, products, question)
    except LLM_UNAVAILABLE_ERRORS:
        pass

    return _format_lookup_products_list(products)


def generate_product_recommendation(db, question):
    products = _order_recommendation_products(
        _filter_relevant_products(
            get_products(db), question, recommendation=True
        ),
        question,
    )
    if not products:
        return "No products in the catalog match those requirements."

    product_text = "\n\n".join(
        [
            f"Product: {p['name']}\n"
            f"Category: {p.get('category') or 'Not specified'}\n"
            f"Description: {p.get('description') or 'Not specified'}\n"
            f"Price: ₹{p['price']}\n"
            f"Stock: {p['stock']}"
            + (
                f"\nSpecifications: {p['specifications']}"
                if p.get("specifications")
                else ""
            )
            for p in products
        ]
    )

    prompt = f"""You are a retail product recommendation assistant.

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
   features; do not broaden a product-type match to unrelated accessories,
   and in shared categories like "Keyboards & Mice" match the exact product type.
5. Interpret common equivalents consistently (for example, wireless and
   Bluetooth; laptop and notebook; bag, backpack, and laptop case), without
   treating unrelated items as equivalent products.
6. If the requirement asks for a lower, lowest, cheaper, or least expensive
   option, recommend in ascending price order (lowest first). If it asks for
   a higher or most expensive option, use descending price order.
7. Recommend each exact catalog product at most once.

Output rules:
- Use only exact products and facts from the catalog; do not invent details.
- First write a brief verification in "analysis", then populate "recommendations".
- Return only valid JSON with this shape:
  {{"analysis":"brief step-by-step evaluation of customer needs vs catalog","recommendations":[{{"product":"exact catalog product name","reason":"brief factual match"}}]}}
- Do not include markdown or code fences."""

    try:
        answer = ask_llm(prompt)
        return _format_recommendation_answer(answer, products, question)
    except LLM_UNAVAILABLE_ERRORS:
        in_stock = [p for p in products if int(p.get("stock") or 0) > 0]
        candidates = in_stock if in_stock else products
        fallback_payload = {
            "recommendations": [
                {
                    "product": p["name"],
                    "reason": (
                        f"{p.get('category') or 'Catalog match'} — "
                        f"{p.get('description') or 'Matches your stated criteria'} "
                        f"(₹{p['price']}, {p['stock']} in stock)."
                    ),
                }
                for p in candidates
            ]
        }
        return _format_recommendation_answer(
            json.dumps(fallback_payload), products, question
        )


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

    # Pre-analyze chronological, explicit-order, and count constraints before calling Ollama
    selected_orders, narrowed, selection_note = _plan_order_selection(orders, question)
    if narrowed and not selected_orders:
        return selection_note or "No matching orders were found for this customer."

    total_customer_orders = len(orders)
    order_entries = []
    for idx, order in enumerate(selected_orders, start=1):
        overall_rank = next(
            (r for r, orig in enumerate(orders, start=1) if orig.order_number == order.order_number),
            idx,
        )
        rank_badge = (
            "LATEST / MOST RECENT ORDER"
            if overall_rank == 1
            else ("OLDEST / FIRST ORDER" if overall_rank == total_customer_orders else f"Rank #{overall_rank} Newest-to-Oldest")
        )
        created_at = getattr(order, "created_at", None)
        date_line = (
            f"\nOrder Date: {created_at.strftime('%Y-%m-%d %H:%M') if hasattr(created_at, 'strftime') else str(created_at)[:16]}"
            if created_at is not None
            else ""
        )
        items_str = ", ".join(
            f"{it.product_name} (x{it.quantity})"
            for it in (getattr(order, "items", None) or [])
            if getattr(it, "product_name", None)
        )
        items_line = f"\nItems: {items_str}" if items_str else ""
        order_entries.append(
            f"[{rank_badge} — {overall_rank} of {total_customer_orders} total orders]\n"
            f"Order Number: {order.order_number}\n"
            f"Status: {order.status}\n"
            f"Amount: ₹{order.total_amount}{date_line}{items_line}"
        )
    order_text = "\n\n".join(order_entries)
    guidance_line = (
        f"\nBackend Query Analysis: {selection_note}\n"
        if selection_note
        else ""
    )

    prompt = f"""You are a senior order support analyst.

Verified Customer Orders (Total orders on file for customer: {total_customer_orders}):
{order_text}
{guidance_line}
Question:
{question}

STRICT REASONING & OUTPUT RULES:
- Use ONLY the verified order data shown above. Do NOT invent order numbers, statuses, delivery dates, or tracking numbers.
- Respect exact quantity and recency constraints: if 1 order or the latest/last order is requested, select ONLY that single verified order ({selected_orders[0].order_number}).
- First write a brief step-by-step verification in "analysis", then write a 1-sentence factual executive answer in "summary", and list the matching exact Order Number(s) in "orders".
- Return ONLY valid JSON with this exact shape:
  {{"analysis":"step-by-step verification of order rank, count, and question","summary":"concise 1-sentence factual answer","orders":["exact Order Number"]}}"""

    try:
        raw_answer = ask_llm(prompt)
        parsed = _extract_json_object(raw_answer)

        if narrowed:
            summary_line = (
                _sanitize_order_summary(parsed.get("summary", ""), selected_orders, orders)
                if isinstance(parsed, dict)
                else ""
            )
            return _format_order_cards(selected_orders, intro=summary_line)

        if isinstance(parsed, dict) and isinstance(parsed.get("orders"), list):
            order_by_code = {
                (o.order_number or "").upper(): o for o in selected_orders
            }
            chosen = []
            seen_codes = set()
            for code in parsed["orders"]:
                norm_code = str(code or "").strip().upper()
                if norm_code in order_by_code and norm_code not in seen_codes:
                    seen_codes.add(norm_code)
                    chosen.append(order_by_code[norm_code])

            target_list = chosen if chosen else selected_orders
            summary_line = _sanitize_order_summary(
                parsed.get("summary", ""), target_list, orders
            )
            return _format_order_cards(target_list, intro=summary_line)

        cleaned_plain = (raw_answer or "").replace("```", "").strip()
        mentioned = [
            o
            for o in selected_orders
            if re.search(rf"(?<![\w-]){re.escape(o.order_number)}(?![\w-])", cleaned_plain, re.I)
        ]
        if mentioned:
            return _format_order_cards(mentioned)
        return cleaned_plain

    except LLM_UNAVAILABLE_ERRORS:
        return _format_order_cards(selected_orders)


def generate_ticket_details(question):
    prompt = f"""You are a senior customer support triage specialist.

Analyze the customer statement below, determine urgency/impact, and draft a clear support ticket.

Customer Statement:
{question}

Priority Classification Rules:
- CRITICAL: Fraud, unauthorized charge, security breach, total service lockout, or explicit executive escalation.
- HIGH: Damaged/broken/defective item, wrong or missing item, failed payment, refund issue, or severe delivery delay.
- MEDIUM: Standard order, product, warranty, or account troubleshooting request.
- LOW: General product question, how-to inquiry, or minor feedback.

Return ONLY valid JSON with this exact format:
{{
  "analysis": "1-sentence assessment of core issue and severity",
  "subject": "concise professional ticket subject under 70 characters",
  "description": "clear factual summary of the customer's issue and requested resolution",
  "priority": "LOW or MEDIUM or HIGH or CRITICAL"
}}"""

    try:
        response = ask_llm(prompt)
        parsed = _extract_json_object(response)
        if not isinstance(parsed, dict):
            raise ValueError("Invalid ticket draft JSON")
        subject = str(parsed.get("subject") or "").replace("**", "").strip()
        description = str(parsed.get("description") or "").replace("**", "").strip()
        priority = str(parsed.get("priority") or "MEDIUM").strip().upper()
        if priority not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            priority = "MEDIUM"
        if not subject or not description:
            raise ValueError("Incomplete ticket draft fields")
        return {
            "subject": subject,
            "description": description,
            "priority": priority,
        }
    except Exception:
        cleaned_q = (question or "").strip()
        first_sentence = re.split(r"[.!?\n]", cleaned_q)[0].strip()
        subject = (
            (first_sentence[:68].rstrip() + "...")
            if len(first_sentence) > 70
            else (first_sentence or "General Support Request")
        )
        lowered = cleaned_q.lower()
        if any(w in lowered for w in ("fraud", "unauthorized", "escalate", "urgent")):
            priority = "CRITICAL"
        elif any(
            w in lowered
            for w in ("damaged", "broken", "wrong", "missing", "refund", "delayed", "failed")
        ):
            priority = "HIGH"
        elif any(w in lowered for w in ("question", "how to", "inquiry")):
            priority = "LOW"
        else:
            priority = "MEDIUM"
        return {
            "subject": subject,
            "description": cleaned_q or "Customer support request",
            "priority": priority,
        }
