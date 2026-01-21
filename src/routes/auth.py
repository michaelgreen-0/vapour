from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import uuid
import redis
from ..services import verify_login 
from ..env import CHALLENGE_LIFETIME, REDIS_HOST, REDIS_PORT

router = APIRouter()
templates = Jinja2Templates(directory="src/templates")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    challenge_id = str(uuid.uuid4())
    challenge = f"Verification Challenge: {challenge_id}"
    redis_client.setex(
        name = challenge_id, 
        time = CHALLENGE_LIFETIME, 
        value = challenge
    )
    
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "challenge": challenge,
        "challenge_id": challenge_id
    })

@router.post("/login")
async def login(
    request: Request, 
    public_key: str = Form(...), 
    signature: str = Form(...),
    challenge_id: str = Form(...)
):
    expected_challenge = redis_client.get(challenge_id)
    if not expected_challenge:
        raise HTTPException(status_code=400, detail="Challenge expired")

    is_valid, user_id = verify_login(public_key, signature, expected_challenge)
    
    if is_valid and user_id:
        redis_client.delete(challenge_id)
        response = RedirectResponse(url="/chat/", status_code=303)
        response.set_cookie(key="user_id", value=user_id, httponly=True)
        return response

    return templates.TemplateResponse("login.html", {
        "request": request,
        "challenge": expected_challenge,
        "challenge_id": challenge_id,
        "error": "Verification Failed"
    })