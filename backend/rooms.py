from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.deps import current_user
from config import settings
from database import rooms as svc
from database.models import User

router = APIRouter(prefix="/api/rooms")


class CreateBody(BaseModel):
    rounds: int = 8


class JoinBody(BaseModel):
    code: str


def _invite_link(code: str) -> str:
    return f"https://t.me/{settings.bot_username}?start=room_{code}"


async def _state(code: str, user: User) -> dict:
    state = await svc.get_state(code, user.id)
    state["invite_link"] = _invite_link(state["code"])
    return state


@router.post("")
async def create(body: CreateBody, user: User = Depends(current_user)):
    code = await svc.create_room(user.id, body.rounds)
    return await _state(code, user)


@router.post("/join")
async def join(body: JoinBody, user: User = Depends(current_user)):
    code = await svc.join_room(body.code, user.id)
    return await _state(code, user)


@router.get("/{code}")
async def state(code: str, user: User = Depends(current_user)):
    return await _state(code, user)


@router.post("/{code}/start")
async def start(code: str, user: User = Depends(current_user)):
    await svc.start_room(code, user.id)
    return await _state(code, user)


@router.post("/{code}/next")
async def next_round(code: str, user: User = Depends(current_user)):
    await svc.next_round(code, user.id)
    return await _state(code, user)


@router.post("/{code}/leave")
async def leave(code: str, user: User = Depends(current_user)):
    await svc.leave_room(code, user.id)
    return {"ok": True}
