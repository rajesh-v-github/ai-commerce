import re

from app.agents.base import AgentAdapter


class MockAgentAdapter(
    AgentAdapter
):

    async def ask(
        self,
        question: str,
        context: dict
    ):

        match = re.search(
            r"ORD-[A-Za-z0-9]+",
            question
        )

        if match:

            return {
                "tool_used":
                "get_order_details",

                "answer":
                f"Retrieved order "
                f"{match.group(0)}",

                "business_data":
                context
            }

        return {
            "tool_used":
            "none",

            "answer":
            "Need order number"
        }
``