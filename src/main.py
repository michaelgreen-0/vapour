from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import pgpy
import uuid
import uvicorn
import traceback
from typing import Dict, Optional

app = FastAPI()
templates = Jinja2Templates(directory="templates")

challenges = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def broadcast(self, message: str, sender: str):
        for connection in self.active_connections.values():
            try:
                await connection.send_text(f"[{sender}]: {message}")
            except:
                pass

manager = ConnectionManager()

def verify_login(public_key_str, clearsigned_str, expected_challenge):
    try:
        clearsigned_str = clearsigned_str.replace('\r\n', '\n').strip()
        public_key_str = public_key_str.strip()

        key, _ = pgpy.PGPKey.from_blob(public_key_str)
        msg = pgpy.PGPMessage.from_blob(clearsigned_str)
        
        if str(msg.message).strip() != expected_challenge.strip():
            print("Challenge mismatch")
            return False, None

        if not msg.signatures:
            print("No signatures")
            return False, None

        signer_id = msg.signatures[0].signer
        known_ids = {key.fingerprint.keyid} | set(key.subkeys)
        
        if signer_id not in known_ids:
            print(f"Signing ID {signer_id} not in known IDs {known_ids}")
            return False, None

        verification = key.verify(msg)
        
        print(f"Verification result: {verification}")
        
        if verification:
            return True, str(key.fingerprint.keyid)
        return False, None

    except Exception as e:
        print(f"Exception: {e}")
        
        traceback.print_exc()
        return False, None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    challenge_id = str(uuid.uuid4())
    challenge = f"Verification Challenge: {challenge_id}"
    challenges[challenge_id] = challenge
    
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "challenge": challenge,
        "challenge_id": challenge_id
    })

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request, 
    public_key: str = Form(...), 
    signature: str = Form(...),
    challenge_id: str = Form(...)
):
    expected_challenge = challenges.get(challenge_id)
    if not expected_challenge:
        return templates.TemplateResponse("login.html", {
            "request": request, "challenge": "Expired", "challenge_id": "", "error": "Challenge expired"
        })

    is_valid, user_id = verify_login(public_key, signature, expected_challenge)
    
    if is_valid and user_id:
        if challenge_id in challenges:
            del challenges[challenge_id]
        
        response = RedirectResponse(url="/chat", status_code=303)
        response.set_cookie(key="user_id", value=user_id)
        return response

    return templates.TemplateResponse("login.html", {
        "request": request,
        "challenge": expected_challenge,
        "challenge_id": challenge_id,
        "error": "Verification Failed"
    })

@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request, user_id: Optional[str] = Cookie(None)):
    if not user_id:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("chat.html", {"request": request, "user_id": user_id})

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        await manager.broadcast(f"User {client_id} joined", "System")
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data, client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast(f"User {client_id} left", "System")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)