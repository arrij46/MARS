from abc import ABC, abstractmethod
from common.a2a import A2AMessage, A2AMessageBroker

class BaseAgent(ABC):
    def __init__(self, name: str, exchange: str = "agents-exchange", queue: str = None):
        self.name = name
        self.status = "idle"
        self.tools = {}
        self.reasoner = None
        self.exchange = exchange
        self.queue = queue or name
        self.message_broker = A2AMessageBroker()  # central broker for publishing/consuming

    def create_message(self, receiver: str, payload: dict, type_: str = "inform", conv_id: str = "") -> A2AMessage:
        """
        Create a fresh A2AMessage instance for each outgoing message.
        Ensures each message is independent.
        """
        return A2AMessage(
            sender=self.name,
            receiver=receiver,
            type=type_,
            payload=payload,
            conv_id=conv_id
        )

    async def send_message(self, receiver: str, payload: dict, type_: str = "inform", conv_id: str = ""):
        """
        Convenience method to send a message via the broker using create_message.
        """
        msg = self.create_message(receiver, payload, type_, conv_id)
        await self.message_broker.publish_message(receiver, msg.dict())

    @abstractmethod
    async def handle_message(self, msg: dict):
        """Each agent must implement its own message handling logic"""
        pass

    @abstractmethod
    async def start_agent(self):
        """Each agent must implement its own start logic"""
        pass
