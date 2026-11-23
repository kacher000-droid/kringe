from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import rooms
from backend.deps import current_user
from database.models import User
from database.rooms import RoomError

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(RoomError)
async def room_error_handler(_request, exc: RoomError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.message})


@app.get("/api/health")
async def health():
    return {"ok": True}


@app.get("/api/me")
async def me(user: User = Depends(current_user)):
    return {
        "id": user.id,
        "display_name": user.display_name,
        "games_played": user.games_played,
        "invited_count": user.invited_count,
        "created_at": user.created_at.isoformat(),
    }


app.include_router(rooms.router)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
