import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from config import settings


class InitDataError(Exception):
    pass


def validate_init_data(init_data: str, max_age: int = 86400) -> dict:
    """Проверяет подпись Telegram WebApp initData и возвращает данные пользователя."""
    if not init_data:
        raise InitDataError("empty")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("no hash")

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise InitDataError("bad hash")

    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except ValueError:
        raise InitDataError("bad auth_date")
    if time.time() - auth_date > max_age:
        raise InitDataError("expired")

    try:
        user = json.loads(pairs["user"])
        int(user["id"])
    except (KeyError, ValueError, TypeError):
        raise InitDataError("no user")
    return user
