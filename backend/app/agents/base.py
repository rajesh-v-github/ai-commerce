from abc import ABC
from abc import abstractmethod


class AgentAdapter(ABC):

    @abstractmethod
    async def ask(
        self,
        question: str,
        context: dict
    ):
        pass