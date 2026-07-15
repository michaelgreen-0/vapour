from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Cookie, status
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
from urllib.parse import urlsplit
import asyncio
import json
import time
from ..services import ConnectionManager, unsign_user_id, is_valid_fingerprint
from ..templating import templates

router = APIRouter(prefix="/chat")
manager = ConnectionManager()

# Largest single WebSocket frame we will parse. An ECDH JWK is a few hundred
# bytes and chat messages are short; this is generous while bounding the JSON a
# hostile client can force us to allocate and parse.
MAX_WS_MESSAGE = 64 * 1024

# Close a socket that sends nothing for this long (slow-loris / idle hoarding).
IDLE_TIMEOUT = 300  # seconds

# Per-connection flood control: at most MAX_MSGS messages per MSG_WINDOW.
MSG_WINDOW = 10  # seconds
MAX_MSGS = 120

# Message types the protocol understands; anything else is rejected.
_ALLOWED_TYPES = {"key_exchange", "encrypted_text"}


@router.get("/", response_class=HTMLResponse)
async def chat_home(request: Request, user_id: Optional[str] = Cookie(None)):
    user_id = unsign_user_id(user_id)
    if not user_id:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(
        "chat.html", {"request": request, "user_id": user_id}
    )


@router.get("/{recipient_id}", response_class=HTMLResponse)
async def conversation(
    request: Request, recipient_id: str, user_id: Optional[str] = Cookie(None)
):
    user_id = unsign_user_id(user_id)
    if not user_id:
        return RedirectResponse(url="/")
    # The recipient is addressed by PGP fingerprint; reject anything else so
    # arbitrary path text never reaches routing/templates/logs.
    if not is_valid_fingerprint(recipient_id):
        return RedirectResponse(url="/chat/")
    return templates.TemplateResponse(
        "conversation.html",
        {"request": request, "user_id": user_id, "recipient_id": recipient_id},
    )


def _origin_allowed(websocket: WebSocket) -> bool:
    """Reject cross-site WebSocket handshakes.

    Browsers always send Origin on a WS upgrade, so we require it to match the
    Host being connected to. Non-browser clients omit Origin; those are allowed
    here because the SameSite=Strict session cookie already prevents a foreign
    site from authenticating one.
    """
    origin = websocket.headers.get("origin")
    if origin is None:
        return True
    host = websocket.headers.get("host")
    return bool(host) and urlsplit(origin).netloc == host


def _valid_message(data) -> bool:
    """Enforce the minimal message schema before routing anything."""
    if not isinstance(data, dict):
        return False
    if data.get("type") not in _ALLOWED_TYPES:
        return False
    if not is_valid_fingerprint(data.get("target_user")):
        return False
    if data["type"] == "key_exchange":
        return isinstance(data.get("publicKey"), dict)
    content = data.get("content")
    return (
        isinstance(content, dict) and "iv" in content and "ciphertext" in content
    )


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket):
    if not _origin_allowed(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = unsign_user_id(websocket.cookies.get("user_id"))
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not manager.has_capacity_for(user_id):
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
        return

    await manager.connect(websocket, user_id)
    window_start = time.monotonic()
    msg_count = 0
    try:
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(), timeout=IDLE_TIMEOUT
                )
            except asyncio.TimeoutError:
                await websocket.close(code=status.WS_1001_GOING_AWAY)
                break

            now = time.monotonic()
            if now - window_start > MSG_WINDOW:
                window_start = now
                msg_count = 0
            msg_count += 1
            if msg_count > MAX_MSGS:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                break

            if len(raw) > MAX_WS_MESSAGE:
                await websocket.close(code=status.WS_1009_MESSAGE_TOO_BIG)
                break

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
                break

            if not _valid_message(data):
                await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
                break

            await manager.send_personal_message(
                message=data, sender=user_id, recipient=data["target_user"]
            )
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)
