import time

from app.agents.tools import (
    get_customer_summary,
    get_latest_order,
    get_customer_360,
    get_ticket_summary,
    recommend_next_action,
    generate_ai_insights,
    generate_copilot_answer,
    get_customer_orders,
    get_customer_tickets,
    get_products,
    generate_product_lookup,
    generate_product_recommendation,
    generate_order_lookup,
    generate_ticket_details,
)


class SupportCopilot:

    @staticmethod
    def assistant(db, request):
        feature = request.feature

        if request.feature == "create_ticket":

            ticket_data = generate_ticket_details(request.question)

            return {"ticket_preview": ticket_data}

        if request.feature == "order_lookup":

            answer = generate_order_lookup(db, request.customer_id, request.question)

            return {"answer": answer}

        if request.feature == "product_lookup":

            answer = generate_product_lookup(db, request.question)

            return {"answer": answer}

        if request.feature == "product_recommendation":

            answer = generate_product_recommendation(db, request.question)

            return {"recommendation": answer}

        if feature == "ticket_summary":
            return SupportCopilot.handle(
                db, request.customer_id, request.ticket_id, "ticket"
            )

        return {"message": "Feature not implemented."}

    @staticmethod
    def handle(db, customer_id, ticket_id, question):

        question = question.lower()

        if question.startswith("ask:"):
            start = time.time()
            customer = get_customer_360(db, customer_id)
            orders = get_customer_orders(db, customer_id)
            tickets = get_customer_tickets(db, customer_id)
            ticket_summary = get_ticket_summary(db, ticket_id)
            user_question = question.replace("ask:", "").strip()

            if "what should i tell the customer" in user_question.lower():

                ai_insights = generate_ai_insights(db, ticket_id)

                return {"copilot_answer": ai_insights["draft_response"]}

            answer = generate_copilot_answer(
                customer,
                orders,
                tickets,
                ticket_summary,
                user_question,
            )

            print(f"Copilot Assistant completed in " f"{time.time() - start:.2f}s")

            return {"copilot_answer": answer}

        # ==========================================
        # DASHBOARD
        # ==========================================

        if "dashboard" in question:

            dashboard_start = time.time()

            print("\n========== DASHBOARD REQUEST ==========")
            print(f"customer_id={customer_id}, " f"ticket_id={ticket_id}")

            start = time.time()
            customer360 = get_customer_360(db, customer_id)
            print(f"Customer360 completed in " f"{time.time() - start:.2f}s")

            start = time.time()
            summary = get_ticket_summary(db, ticket_id)
            print(f"Ticket Summary completed in " f"{time.time() - start:.2f}s")

            if not summary:
                return {"error": "Ticket not found"}

            start = time.time()
            action = recommend_next_action(db, ticket_id)
            print(f"Next Action completed in " f"{time.time() - start:.2f}s")

            start = time.time()
            ai_insights = generate_ai_insights(db, ticket_id)
            print(f"AI Insights completed in " f"{time.time() - start:.2f}s")

            ticket = summary["ticket"]

            result = {
                "executive_summary": {
                    "ticket_id": ticket.id,
                    "subject": ticket.subject,
                    "status": ticket.status,
                    "priority": action["priority"],
                    "issue_summary": ai_insights["executive_summary"]["issue_summary"],
                    "current_status": ai_insights["executive_summary"][
                        "current_status"
                    ],
                    "key_customer_concern": ai_insights["executive_summary"][
                        "key_customer_concern"
                    ],
                    "recommended_next_action": ai_insights["executive_summary"][
                        "recommended_next_action"
                    ],
                },
                "customer_360": customer360,
                "ticket_summary": summary,
                "draft_response": {
                    "subject": ticket.subject,
                    "current_status": ticket.status,
                    "message": ai_insights["draft_response"],
                },
                "next_action": action,
            }

            total_time = time.time() - dashboard_start

            print(f"Dashboard completed in " f"{total_time:.2f}s")

            print("=======================================\n")

            return result

        # ==========================================
        # CUSTOMER 360
        # ==========================================

        if "360" in question:

            customer = get_customer_360(db, customer_id)

            if not customer:
                return "Customer not found."

            latest_order = customer["latest_order"]

            if latest_order:
                order_text = f"{latest_order.order_number} " f"({latest_order.status})"
            else:
                order_text = "No orders found."

            return (
                f"Customer: {customer['username']}\n"
                f"Role: {customer['role']}\n\n"
                f"Total Orders: {customer['total_orders']}\n"
                f"Latest Order: {order_text}\n\n"
                f"Total Tickets: {customer['total_tickets']}\n"
                f"Open Tickets: {customer['open_tickets']}"
            )

        # ==========================================
        # NEXT ACTION
        # ==========================================

        elif "next action" in question:

            recommendation = recommend_next_action(db, ticket_id)

            if not recommendation:
                return {"error": "Ticket not found"}

            return {
                "next_action": {
                    "ticket_id": recommendation["ticket_id"],
                    "subject": recommendation["subject"],
                    "ticket_status": recommendation["status"],
                    "recommended_action": recommendation["recommended_action"],
                }
            }

        # ==========================================
        # DRAFT RESPONSE
        # ==========================================

        elif "draft response" in question:

            start = time.time()

            ai_insights = generate_ai_insights(db, ticket_id)

            print(f"AI Draft completed in " f"{time.time() - start:.2f}s")

            summary = get_ticket_summary(db, ticket_id)

            if not summary:
                return {"error": "Ticket not found"}

            ticket = summary["ticket"]

            return {
                "draft_response": {
                    "subject": ticket.subject,
                    "current_status": ticket.status,
                    "message": ai_insights["draft_response"],
                }
            }

        # ==========================================
        # EXECUTIVE SUMMARY
        # ==========================================

        elif "executive summary" in question:

            start = time.time()

            ai_insights = generate_ai_insights(db, ticket_id)

            print(f"Executive Summary completed in " f"{time.time() - start:.2f}s")

            summary = get_ticket_summary(db, ticket_id)

            recommendation = recommend_next_action(db, ticket_id)

            if not summary:
                return {"error": "Ticket not found"}

            ticket = summary["ticket"]

            return {
                "executive_summary": {
                    "ticket_id": ticket.id,
                    "subject": ticket.subject,
                    "status": ticket.status,
                    "priority": recommendation["priority"],
                    **ai_insights["executive_summary"],
                }
            }

        # ==========================================
        # CUSTOMER SUMMARY
        # ==========================================

        elif "summary" in question:

            summary = get_customer_summary(db, customer_id)

            return (
                f"Customer has "
                f"{summary['orders']} orders "
                f"and "
                f"{summary['tickets']} tickets."
            )

        # ==========================================
        # LATEST ORDER
        # ==========================================

        elif "latest order" in question:

            order = get_latest_order(db, customer_id)

            if not order:
                return "No orders found."

            return (
                f"Latest order "
                f"{order.order_number} "
                f"is currently "
                f"{order.status}."
            )

        # ==========================================
        # TICKET SUMMARY
        # ==========================================

        elif "ticket" in question:

            summary = get_ticket_summary(db, ticket_id)

            if not summary:
                return "Ticket not found."

            ticket = summary["ticket"]

            status_history = "No status changes."

            if summary["history"]:
                status_history = " -> ".join([h.new_status for h in summary["history"]])

            recent_messages = []

            for message in summary["messages"][-3:]:

                recent_messages.append(
                    {
                        "message_id": message.id,
                        "username": message.user.username,
                        "role": message.user.role,
                        "message": message.message,
                        "created_at": message.created_at,
                    }
                )

            return {
                "ticket_summary": {
                    "subject": ticket.subject,
                    "status": ticket.status,
                    "status_history": status_history,
                    "recent_messages": recent_messages,
                }
            }

        return "Unable to answer the question."
