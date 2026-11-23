import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _req(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Не задана переменная {name}")
    return value


def _webapp_url() -> str:
    # Локально адрес подставляет run.sh (туннель), на Render он берётся автоматически.
    url = os.getenv("WEBAPP_URL", "").strip() or os.getenv("RENDER_EXTERNAL_URL", "").strip()
    if not url:
        raise SystemExit("Не задан адрес Mini App (WEBAPP_URL). Локально запускай через bash run.sh")
    return url.rstrip("/")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    webapp_url: str
    bot_username: str
    host: str
    port: int
    database_url: str


settings = Settings(
    bot_token=_req("BOT_TOKEN"),
    webapp_url=_webapp_url(),
    bot_username=os.getenv("BOT_USERNAME", "KRINZzH_Bot").lstrip("@"),
    host="0.0.0.0" if os.getenv("RENDER") else os.getenv("HOST", "127.0.0.1"),
    port=int(os.getenv("PORT", "8000")),
    database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./kringe.db"),
)
