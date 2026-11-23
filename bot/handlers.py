import html

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from config import settings
from database.rooms import normalize_code, valid_code
from database.users import get_or_create_user

router = Router()
router.message.filter(F.chat.type == "private")

HELP_TEXT = (
    "<b>Как играть</b>\n\n"
    "1. Один создаёт игру и кидает друзьям ссылку.\n"
    "2. Вас должно быть от 3 до 10.\n"
    "3. Каждый раунд — вопрос вроде «Кто первым продаст друзей за Wi-Fi?». "
    "Все голосуют за одного из компании.\n"
    "4. В конце получаете титулы и карточку, которой не стыдно поделиться.\n\n"
    "Мы не осуждаем. Мы просто всё запомнили."
)


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 ОТКРЫТЬ ИГРУ", web_app=WebAppInfo(url=settings.webapp_url))],
            [InlineKeyboardButton(text="❓ Как играть", callback_data="help")],
        ]
    )


def room_keyboard(code: str) -> InlineKeyboardMarkup:
    url = f"{settings.webapp_url}/?room={code}"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🚪 ЗАЙТИ В КОМНАТУ", web_app=WebAppInfo(url=url))]]
    )


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    tg = message.from_user
    args = command.args or ""

    referrer_id = None
    if args.startswith("ref_"):
        try:
            referrer_id = int(args[4:])
        except ValueError:
            pass

    user, created = await get_or_create_user(tg.id, tg.username, tg.first_name, referrer_id)
    if user.is_banned:
        await message.answer("Доступ закрыт.")
        return

    if args.startswith("room_"):
        code = normalize_code(args[5:])
        if valid_code(code):
            await message.answer(
                f"<b>КТО ТУТ КРИНЖ?</b>\n\n"
                f"Тебя зовут в игру. Код комнаты: <code>{code}</code>",
                reply_markup=room_keyboard(code),
            )
            return

    name = html.escape(user.display_name)
    greeting = "Добро пожаловать" if created else "С возвращением"
    await message.answer(
        f"<b>КТО ТУТ КРИНЖ?</b>\n\n"
        f"{greeting}, {name}.\n"
        f"Проверь, кто в вашей компании самый подозрительный персонаж.",
        reply_markup=main_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, reply_markup=main_keyboard())


@router.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery):
    await call.message.answer(HELP_TEXT)
    await call.answer()
