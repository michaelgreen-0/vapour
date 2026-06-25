from typing import Dict, Optional
from fastapi import WebSocket

# Hard ceiling on simultaneously held sockets. Each connection costs memory and
# an event-loop task; this bounds how much a flood of distinct identities can
# tie up before new connections are shed (1013 Try Again Later).
MAX_CONNECTIONS = 500


class ConnectionManager:
    def __init__(self, max_connections: int = MAX_CONNECTIONS):
        self.active_connections: Dict[str, WebSocket] = {}
        self.max_connections = max_connections

    def has_capacity_for(self, user_id: str) -> bool:
        """Whether a (re)connection from ``user_id`` can be accepted.

        A reconnecting user replaces their own existing slot, so they always
        fit; only genuinely new identities count against the cap.
        """
        if user_id in self.active_connections:
            return True
        return len(self.active_connections) < self.max_connections

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str, websocket: Optional[WebSocket] = None):
        """Drop ``user_id``'s connection.

        If ``websocket`` is given, only remove it when it is still the active
        socket for that user, so a late cleanup from a replaced connection
        cannot evict the user's newer one.
        """
        current = self.active_connections.get(user_id)
        if current is None:
            return
        if websocket is not None and current is not websocket:
            return
        del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, sender: str, recipient: str):
        if recipient in self.active_connections:
            payload_for_recipient = message.copy()
            payload_for_recipient["sender"] = sender
            await self.active_connections[recipient].send_json(payload_for_recipient)

        if sender in self.active_connections:
            payload_for_sender = message.copy()
            payload_for_sender["recipient"] = recipient
            await self.active_connections[sender].send_json(payload_for_sender)
