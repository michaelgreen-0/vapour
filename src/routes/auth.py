from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import run_in_threadpool
import uuid
import redis
from ..services import verify_login, client_ip, is_rate_limited
from ..env import CHALLENGE_LIFETIME, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

router = APIRouter()
templates = Jinja2Templates(directory="src/templates")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD or None,
    decode_responses=True,
)

# Largest PGP public key / clearsigned blob we will even attempt to parse.
# A normal armored key is a few KB; this is generous while blocking giant
# payloads that exist only to burn CPU/memory in pgpy.
MAX_PGP_FIELD = 16 * 1024


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if is_rate_limited(redis_client, client_ip(request), "index", limit=60, window=60):
        raise HTTPException(status_code=429, detail="Too Many Requests")

    challenge_id = str(uuid.uuid4())
    challenge = f"Verification Challenge: {challenge_id}"
    redis_client.setex(name=challenge_id, time=CHALLENGE_LIFETIME, value=challenge)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "challenge": challenge, "challenge_id": challenge_id},
    )


@router.post("/login")
async def login(
    request: Request,
    public_key: str = Form(...),
    signature: str = Form(...),
    challenge_id: str = Form(...),
):
    if is_rate_limited(redis_client, client_ip(request), "login", limit=30, window=60):
        raise HTTPException(status_code=429, detail="Too Many Requests")

    if len(public_key) > MAX_PGP_FIELD or len(signature) > MAX_PGP_FIELD:
        raise HTTPException(status_code=413, detail="Payload too large")

    expected_challenge = redis_client.get(challenge_id)
    if not expected_challenge:
        raise HTTPException(status_code=400, detail="Challenge expired")

    # pgpy verification is synchronous and CPU-heavy on attacker-controlled
    # input; run it off the event loop so one slow/malicious key can't stall
    # every other connection.
    is_valid, user_id = await run_in_threadpool(
        verify_login, public_key, signature, expected_challenge
    )

    if is_valid and user_id:
        redis_client.delete(challenge_id)
        response = RedirectResponse(url="/chat/", status_code=303)
        response.set_cookie(key="user_id", value=user_id, httponly=True)
        return response

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "challenge": expected_challenge,
            "challenge_id": challenge_id,
            "error": "Verification Failed",
        },
    )
