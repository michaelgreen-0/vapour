from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
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
