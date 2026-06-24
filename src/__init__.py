from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import logging.config
from .logger import LOGGING_CONFIG
from .routes import auth, chat

logging.config.dictConfig(LOGGING_CONFIG)

app = FastAPI()

# Largest request body we accept, mirroring the reverse proxy's cap. Enforced in
# the app so onion traffic -- which is pointed straight at Uvicorn and bypasses
# Caddy -- gets the same bound.
MAX_BODY_BYTES = 64 * 1024

# Applied to every response, including over the onion service which does not go
# through Caddy. script-src/style-src 'self' is only safe because all scripts and
# styles live in /static (no inline scripts, styles, or event handlers).
SECURITY_HEADERS = {
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self'; base-uri 'none'; "
        "frame-ancestors 'none'; form-action 'self'"
    ),
}


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            too_large = int(content_length) > MAX_BODY_BYTES
        except ValueError:
            return PlainTextResponse("Bad Request", status_code=400)
        if too_large:
            return PlainTextResponse("Payload too large", status_code=413)

    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    # Don't advertise the server software.
    response.headers["Server"] = "vapour"
    return response


app.mount("/static", StaticFiles(directory="src/static"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("src/static/favicon.ico")


app.include_router(auth.router)
app.include_router(chat.router)
