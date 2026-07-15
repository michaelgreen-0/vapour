from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.concurrency import run_in_threadpool
import uuid
import redis
from ..templating import templates
from ..services import (
    verify_login,
    client_ip,
    is_rate_limited,
    is_globally_rate_limited,
    sign_user_id,
)
from ..env import (
    CHALLENGE_LIFETIME,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PASSWORD,
    SESSION_LIFETIME,
)

router = APIRouter()

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


def _issue_challenge() -> tuple[str, str]:
    """Mint a fresh single-use challenge and store it in Redis with a TTL."""
    challenge_id = str(uuid.uuid4())
    challenge = f"Verification Challenge: {challenge_id}"
    redis_client.setex(name=challenge_id, time=CHALLENGE_LIFETIME, value=challenge)
    return challenge, challenge_id


def _render_login(
    request: Request,
    challenge: str,
    challenge_id: str,
    error: str | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "challenge": challenge,
            "challenge_id": challenge_id,
            "error": error,
        },
        status_code=status_code,
    )


def _challenge_to_show(expected_challenge, challenge_id) -> tuple[str, str]:
    """Reuse the still-valid challenge, or mint a fresh one if it's gone."""
    if expected_challenge:
        return expected_challenge, challenge_id
    return _issue_challenge()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if is_rate_limited(redis_client, client_ip(request), "index", limit=60, window=60):
        raise HTTPException(status_code=429, detail="Too Many Requests")

    challenge, challenge_id = _issue_challenge()
    return _render_login(request, challenge, challenge_id)


@router.post("/login")
async def login(
    request: Request,
    # Defaulted (not required) so empty/missing fields reach our own validation
    # and render a friendly message, instead of FastAPI's raw 422 JSON dump.
    public_key: str = Form(""),
    signature: str = Form(""),
    challenge_id: str = Form(""),
):
    # Per-IP limit (clearnet) plus a server-wide ceiling that also covers onion
    # traffic, where every client shares the exempt loopback address.
    if is_rate_limited(
        redis_client, client_ip(request), "login", limit=30, window=60
    ) or is_globally_rate_limited(redis_client, "login", limit=300, window=60):
        raise HTTPException(status_code=429, detail="Too Many Requests")

    expected_challenge = redis_client.get(challenge_id) if challenge_id else None

    # Missing input: re-show the page (keeping the existing challenge if it's
    # still valid, otherwise a fresh one) with guidance.
    if not public_key.strip() or not signature.strip():
        challenge, challenge_id = _challenge_to_show(expected_challenge, challenge_id)
        return _render_login(
            request,
            challenge,
            challenge_id,
            "Please paste both your PGP public key and the clearsigned challenge "
            "before logging in.",
            status_code=400,
        )

    if len(public_key) > MAX_PGP_FIELD or len(signature) > MAX_PGP_FIELD:
        challenge, challenge_id = _challenge_to_show(expected_challenge, challenge_id)
        return _render_login(
            request,
            challenge,
            challenge_id,
            "That input is too large. Paste only your public key and the signed "
            "challenge, nothing more.",
            status_code=413,
        )

    if not expected_challenge:
        # The challenge they signed has expired (or was never issued). Give them
        # a fresh one to sign rather than a dead end.
        challenge, challenge_id = _issue_challenge()
        return _render_login(
            request,
            challenge,
            challenge_id,
            "Your login challenge expired. Here is a new one — please sign it and "
            "try again.",
            status_code=400,
        )

    # pgpy verification is synchronous and CPU-heavy on attacker-controlled
    # input; run it off the event loop so one slow/malicious key can't stall
    # every other connection.
    is_valid, user_id = await run_in_threadpool(
        verify_login, public_key, signature, expected_challenge
    )

    if is_valid and user_id:
        redis_client.delete(challenge_id)
        response = RedirectResponse(url="/chat/", status_code=303)
        response.set_cookie(
            key="user_id",
            value=sign_user_id(user_id),
            # Cap the cookie's browser lifetime to the signed token's lifetime.
            # The server also enforces expiry from the signed issue time, so
            # this is just so well-behaved clients drop it on their own.
            max_age=SESSION_LIFETIME,
            httponly=True,
            # https on clearnet (via Caddy's X-Forwarded-Proto); the onion
            # service is plain http, where a Secure cookie would never be sent.
            secure=request.url.scheme == "https",
            samesite="strict",
        )
        return response

    # The challenge is single-use but only consumed on success, so it is still
    # valid here -- keep showing it so the user can fix their key/signature and
    # retry against the same challenge.
    return _render_login(
        request,
        expected_challenge,
        challenge_id,
        "Verification failed. Make sure you clearsigned the exact challenge above "
        "with the key whose public block you pasted.",
        status_code=401,
    )


@router.post("/logout")
async def logout(request: Request):
    """Clear the session cookie and return to the login page.

    Sessions are stateless (signed cookies), so this clears the client's copy.
    Tokens still expire on their own via SESSION_LIFETIME; server-side
    revocation of a leaked-but-unexpired token is tracked as future work.
    """
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(
        key="user_id",
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
    )
    return response
