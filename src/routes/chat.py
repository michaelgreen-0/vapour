from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Cookie, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import json
from ..services import ConnectionManager

router = APIRouter(prefix="/chat")
templates = Jinja2Templates(directory="src/templates")
manager = ConnectionManager()


@router.get("/", response_class=HTMLResponse)
async def chat_home(request: Request, user_id: Optional[str] = Cookie(None)):
    if not user_id:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(
        "chat.html", {"request": request, "user_id": user_id}
    )


@router.get("/{recipient_id}", response_class=HTMLResponse)
async def conversation(
    request: Request, recipient_id: str, user_id: Optional[str] = Cookie(None)
):
    if not user_id:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(
        "conversation.html",
        {"request": request, "user_id": user_id, "recipient_id": recipient_id},
    )


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
):
    user_id = websocket.cookies.get("user_id")

    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.send_personal_message(
                message=data, sender=user_id, recipient=data.get("target_user")
            )
    except (WebSocketDisconnect, json.JSONDecodeError):
        manager.disconnect(user_id)
