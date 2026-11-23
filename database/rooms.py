import random
import secrets

from sqlalchemy import delete, func, select

from database.models import Question, Room, RoomPlayer, User
from database.session import SessionLocal

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6
MIN_PLAYERS = 3
MAX_PLAYERS = 10
ALLOWED_ROUNDS = (5, 8)


class RoomError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def normalize_code(code: str | None) -> str:
    return (code or "").strip().upper()


def valid_code(code: str) -> bool:
    return len(code) == CODE_LENGTH and all(c in CODE_ALPHABET for c in code)


async def _get_room(session, code: str) -> Room:
    code = normalize_code(code)
    if not valid_code(code):
        raise RoomError(404, "Комната не найдена")
    room = await session.scalar(select(Room).where(Room.code == code))
    if room is None:
        raise RoomError(404, "Комната не найдена")
    return room


async def _count_players(session, room_id: int) -> int:
    return await session.scalar(
        select(func.count()).select_from(RoomPlayer).where(RoomPlayer.room_id == room_id)
    )


async def create_room(host_id: int, rounds: int) -> str:
    rounds = rounds if rounds in ALLOWED_ROUNDS else 8
    async with SessionLocal() as session:
        # у ведущего одна активная комната: старые закрываем
        old_rooms = await session.scalars(
            select(Room).where(Room.host_id == host_id, Room.status != "finished")
        )
        for old in old_rooms:
            old.status = "finished"

        for _ in range(20):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if await session.scalar(select(Room.id).where(Room.code == code)) is None:
                break
        else:
            raise RoomError(500, "Не удалось создать комнату, попробуй ещё раз")

        room = Room(code=code, host_id=host_id, rounds_total=rounds)
        session.add(room)
        await session.flush()
        session.add(RoomPlayer(room_id=room.id, user_id=host_id))
        await session.commit()
        return code


async def join_room(code: str, user_id: int) -> str:
    async with SessionLocal() as session:
        room = await _get_room(session, code)
        if await session.get(RoomPlayer, (room.id, user_id)) is not None:
            return room.code
        if room.status != "lobby":
            raise RoomError(409, "Игра уже идёт или закончилась")
        if await _count_players(session, room.id) >= MAX_PLAYERS:
            raise RoomError(409, f"В комнате уже {MAX_PLAYERS} игроков")
        session.add(RoomPlayer(room_id=room.id, user_id=user_id))
        await session.commit()
        return room.code


async def leave_room(code: str, user_id: int) -> None:
    async with SessionLocal() as session:
        room = await _get_room(session, code)
        if room.status != "lobby":
            return
        await session.execute(
            delete(RoomPlayer).where(RoomPlayer.room_id == room.id, RoomPlayer.user_id == user_id)
        )
        if room.host_id == user_id:
            room.status = "finished"
        await session.commit()


async def get_state(code: str, user_id: int) -> dict:
    async with SessionLocal() as session:
        room = await _get_room(session, code)
        if await session.get(RoomPlayer, (room.id, user_id)) is None:
            raise RoomError(403, "Ты не в этой комнате")

        rows = await session.execute(
            select(User.id, User.display_name)
            .join(RoomPlayer, RoomPlayer.user_id == User.id)
            .where(RoomPlayer.room_id == room.id)
            .order_by(RoomPlayer.joined_at)
        )
        players = [
            {"id": uid, "name": name, "is_host": uid == room.host_id} for uid, name in rows.all()
        ]

        state = {
            "code": room.code,
            "status": room.status,
            "host_id": room.host_id,
            "players": players,
            "min_players": MIN_PLAYERS,
            "max_players": MAX_PLAYERS,
            "round": room.current_round + 1,
            "rounds_total": room.rounds_total,
            "question": None,
        }

        if room.status == "playing":
            ids = [int(x) for x in room.question_ids.split(",") if x]
            if 0 <= room.current_round < len(ids):
                q = await session.get(Question, ids[room.current_round])
                if q is not None:
                    state["question"] = {"text": q.text, "category": q.category}
        return state


async def start_room(code: str, user_id: int) -> None:
    async with SessionLocal() as session:
        room = await _get_room(session, code)
        if room.host_id != user_id:
            raise RoomError(403, "Начать игру может только ведущий")
        if room.status != "lobby":
            raise RoomError(409, "Игра уже началась")
        if await _count_players(session, room.id) < MIN_PLAYERS:
            raise RoomError(400, f"Нужно минимум {MIN_PLAYERS} игрока")

        ids = list(await session.scalars(select(Question.id).where(Question.is_active.is_(True))))
        if not ids:
            raise RoomError(500, "В базе нет вопросов")
        chosen = random.sample(ids, min(room.rounds_total, len(ids)))

        room.question_ids = ",".join(str(i) for i in chosen)
        room.rounds_total = len(chosen)
        room.current_round = 0
        room.status = "playing"
        await session.commit()


async def next_round(code: str, user_id: int) -> None:
    async with SessionLocal() as session:
        room = await _get_room(session, code)
        if room.host_id != user_id:
            raise RoomError(403, "Листать вопросы может только ведущий")
        if room.status != "playing":
            raise RoomError(409, "Игра сейчас не идёт")
        room.current_round += 1
        if room.current_round >= room.rounds_total:
            room.current_round = room.rounds_total - 1
            room.status = "finished"
        await session.commit()
