import asyncio
import logging

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import MenuButtonWebApp, WebAppInfo

from backend.api import app
from bot.handlers import router
from config import settings
from database.seed import seed_questions
from database.session import init_db


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await init_db()
    await seed_questions()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="ИГРАТЬ", web_app=WebAppInfo(url=settings.webapp_url))
    )

    server = uvicorn.Server(
        uvicorn.Config(app, host=settings.host, port=settings.port, log_level="warning")
    )
    tasks = {
        asyncio.create_task(server.serve()),
        asyncio.create_task(dp.start_polling(bot, handle_signals=False)),
    }
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for t in done:
            t.result()
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
