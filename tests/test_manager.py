import asyncio
import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.services.manager import ConnectionManager


class TestConnectionManager(unittest.TestCase):
    def setUp(self):
        self.manager = ConnectionManager()

    def test_connect(self):
        async def run_test():
            user_id = "test_user"
            websocket = AsyncMock()
            await self.manager.connect(websocket, user_id)
            self.assertIn(user_id, self.manager.active_connections)
            self.assertEqual(self.manager.active_connections[user_id], websocket)
            websocket.accept.assert_awaited_once()

        asyncio.run(run_test())

    def test_disconnect(self):
        user_id = "test_user"
        self.manager.active_connections[user_id] = AsyncMock()
        self.manager.disconnect(user_id)
        self.assertNotIn(user_id, self.manager.active_connections)

    def test_disconnect_non_existent_user(self):
        user_id = "test_user"
        self.manager.disconnect(user_id)
        self.assertNotIn(user_id, self.manager.active_connections)

    def test_send_personal_message(self):
        async def run_test():
            sender_id = "sender"
            recipient_id = "recipient"
            sender_ws = AsyncMock()
            recipient_ws = AsyncMock()
            self.manager.active_connections[sender_id] = sender_ws
            self.manager.active_connections[recipient_id] = recipient_ws
            message = {"message": "hello"}

            await self.manager.send_personal_message(message, sender_id, recipient_id)

            sender_ws.send_json.assert_awaited_once_with(
                {"message": "hello", "recipient": recipient_id}
            )
            recipient_ws.send_json.assert_awaited_once_with(
                {"message": "hello", "sender": sender_id}
            )

        asyncio.run(run_test())

    def test_send_personal_message_recipient_not_connected(self):
        async def run_test():
            sender_id = "sender"
            recipient_id = "recipient"
            sender_ws = AsyncMock()
            self.manager.active_connections[sender_id] = sender_ws
            message = {"message": "hello"}

            await self.manager.send_personal_message(message, sender_id, recipient_id)

            sender_ws.send_json.assert_awaited_once_with(
                {"message": "hello", "recipient": recipient_id}
            )

        asyncio.run(run_test())

    def test_send_personal_message_sender_not_connected(self):
        async def run_test():
            sender_id = "sender"
            recipient_id = "recipient"
            recipient_ws = AsyncMock()
            self.manager.active_connections[recipient_id] = recipient_ws
            message = {"message": "hello"}

            await self.manager.send_personal_message(message, sender_id, recipient_id)

            recipient_ws.send_json.assert_awaited_once_with(
                {"message": "hello", "sender": sender_id}
            )

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
