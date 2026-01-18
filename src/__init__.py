from fastapi import FastAPI
from fastapi.responses import FileResponse
from .routes import auth, chat

app = FastAPI()

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("src/static/favicon.ico")

app.include_router(auth.router)
app.include_router(chat.router)