from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import logging.config
from .logger import LOGGING_CONFIG
from .routes import auth, chat

logging.config.dictConfig(LOGGING_CONFIG)

app = FastAPI()

app.mount("/static", StaticFiles(directory="src/static"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("src/static/favicon.ico")


app.include_router(auth.router)
app.include_router(chat.router)
