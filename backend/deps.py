from fastapi import Header, HTTPException

from backend.security import InitDataError, validate_init_data
from database.models import User
from database.users import get_or_create_user


async def current_user(x_init_data: str = Header(default="")) -> User:
    try:
        tg_user = validate_init_data(x_init_data)
    except InitDataError:
        raise HTTPException(status_code=401, detail="Открой игру через Telegram-бота")

    user, _ = await get_or_create_user(
        int(tg_user["id"]), tg_user.get("username"), tg_user.get("first_name", "")
    )
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Доступ закрыт")
    return user
