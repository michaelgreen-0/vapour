from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from .logger import MaskingFilter
from .routes import auth, chat

logging.getLogger().addFilter(MaskingFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    mask_filter = MaskingFilter()
    target_loggers = [
        "",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
    ]
    for name in target_loggers:
        logger = logging.getLogger(name)
        logger.addFilter(mask_filter)
        logger.propagate = True
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="src/static"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("src/static/favicon.ico")


app.include_router(auth.router)
app.include_router(chat.router)
