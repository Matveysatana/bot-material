import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.enums import ChatMemberStatus
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_URL = os.getenv("CHANNEL_URL")
SITE_URL = "https://satanovski.ru/"

PDF_PATH = os.path.join("files", "checklist.pdf")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

cached_pdf_file_id: str | None = None

WELCOME_TEXT = (
    "👋 Привет, <b>{name}</b>!\n"
    "\n"
    "Меня зовут <b>Матвей Сатановский</b> — мне 16, "
    "и я занимаюсь разработкой, дизайном "
    "и видеомонтажом для бизнес-проектов.\n"
    "\n"
    "<blockquote>"
    "16 лет — не повод быть посредственным.\n"
    "Я амбициозен, заряжен и думаю на годы вперёд."
    " Каждый проект — это вклад в репутацию,"
    " поэтому работаю с полной отдачей."
    " Путешествую, читаю, тренируюсь, генерирую идеи —"
    " и всё это отражается в том, что я создаю.\n\n"
    "Люблю жизнь и наслаждаюсь ей ❤️\n"
    "</blockquote>\n"
    "\n"
    "🎁 Специально для тебя я подготовил\n"
    "<b>бесплатный материал</b>:\n"
    "\n"
    "📋 <b>«Чек-лист ТОП-10 ошибок, которые "
    "убивают конверсию вашего сайта»</b>\n"
    "\n"
    "Внутри:\n"
    "• 10 критических ошибок с реальными примерами\n"
    "• Готовые решения для каждой проблемы\n"
    "• Советы, которые можно внедрить уже сегодня\n"
    "\n"
    "Нажми кнопку ниже, чтобы забрать 👇"
)

NOT_SUBSCRIBED_TEXT = (
    "😔 Ты пока <b>не подписан</b> на канал.\n"
    "\n"
    "А там — <b>реально много пользы</b>:\n"
    "\n"
    "🧠 Саморазвитие и мышление\n"
    "💼 Бизнес, digital и маркетинг\n"
    "🏋️ Спорт и здоровье\n"
    "🚀 Личный бренд и рост\n"
    "✨ Лайфстайл и полезные лайфхаки\n"
    "\n"
    "📌 <b>Чтобы получить подарок:</b>\n"
    "\n"
    "1️⃣ Нажми <b>«📢 Перейти на канал»</b>\n"
    "2️⃣ Подпишись\n"
    "3️⃣ Вернись и нажми <b>«🔄 Проверить подписку»</b>\n"
    "\n"
    "И чек-лист — твой! 🎁"
)

SUCCESS_TEXT = (
    "🎉 Отлично, <b>{name}</b>!\n"
    "\n"
    "Подписка подтверждена ✅\n"
    "Держи свой подарок 👇\n"
    "\n"
    "📋 <b>«Чек-лист ТОП-10 ошибок, которые убивают конверсию вашего сайта»</b>\n"
    "\n"
    "Изучай, внедряй и наблюдай\n"
)

STILL_NOT_SUBSCRIBED_TEXT = (
    "🤔 Хм, подписки всё ещё нет…\n"
    "\n"
    "Убедись, что нажал <b>«Подписаться»</b>\n"
    "в канале, а потом снова нажми\n"
    "<b>«🔄 Проверить подписку»</b> 👇"
)

SITE_TEXT = (
    "<b>Официальный сайт Матвея Сатановского</b>\n"
    "\n"
    "Здесь ты найдёшь всё, что я делаю:\n"
    "\n"
    "🎬 <b>Видеомонтаж</b> — динамичные ролики "
    "для бизнеса, рилсы, клипы и контент для соцсетей\n\n"
    "💻 <b>Веб-разработка</b> — сайты, лендинги "
    "и боты, которые приносят заявки\n\n"
    "🎨 <b>Дизайн</b> — визуальные решения, "
    "которые выделяют бренд среди конкурентов\n\n"
    "\n"
    "Можешь посмотреть портфолио, изучить услуги "
    "и сразу оставить заявку.\n"
    "\n"
    "👇 Переходи и смотри сам:"
)

LOADING_TEXT = "⏳ Секунду, проверяю..."
FADE_TEXT = "⠀"


def welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎁 Получить материал",
                    callback_data="get_material",
                )
            ],
        ]
    )


def subscribe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Перейти на канал",
                    url=CHANNEL_URL,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Проверить подписку",
                    callback_data="check_subscription",
                )
            ],
        ]
    )


def site_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 Перейти на сайт",
                    url=SITE_URL,
                )
            ],
        ]
    )


async def is_user_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id,
        )
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        )
    except Exception as e:
        logger.error(f"Ошибка проверки подписки для {user_id}: {e}")
        return False


async def fade_out(message) -> None:
    try:
        await message.edit_text(LOADING_TEXT, parse_mode="HTML")
    except Exception:
        pass

    await asyncio.sleep(0.7)

    try:
        await message.edit_text(FADE_TEXT)
    except Exception:
        pass

    await asyncio.sleep(0.4)

    try:
        await message.delete()
    except Exception:
        pass

    await asyncio.sleep(0.2)


async def send_pdf(chat_id: int, name: str) -> None:
    global cached_pdf_file_id

    await bot.send_message(
        chat_id=chat_id,
        text=SUCCESS_TEXT.format(name=name),
        parse_mode="HTML",
    )

    await asyncio.sleep(0.5)

    if cached_pdf_file_id:
        await bot.send_document(
            chat_id=chat_id,
            document=cached_pdf_file_id,
            caption="📎 Твой чек-лист готов. Приятного изучения!",
            parse_mode="HTML",
        )
        logger.info(f"📦 PDF отправлен из кэша пользователю {chat_id}")

    else:
        document = FSInputFile(
            PDF_PATH,
            filename="Чек-лист_ТОП-10_ошибок_конверсии.pdf",
        )
        msg = await bot.send_document(
            chat_id=chat_id,
            document=document,
            caption="📎 Твой чек-лист готов. Приятного изучения!",
            parse_mode="HTML",
        )
        cached_pdf_file_id = msg.document.file_id
        logger.info(
            f"📦 PDF отправлен с диска, file_id сохранён. "
            f"Пользователь: {chat_id}"
        )


async def health_check(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def start_fake_server() -> None:
    port = int(os.getenv("PORT", 10000))

    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"🌐 HTTP-сервер запущен на порту {port}")


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user = message.from_user
    name = user.first_name or (
        f"@{user.username}" if user.username else "друг"
    )

    logger.info(
        f"Пользователь {user.id} ({user.username or 'no_username'}) "
        f"нажал /start | source={command.args}"
    )

    await message.answer(
        WELCOME_TEXT.format(name=name),
        parse_mode="HTML",
        reply_markup=welcome_keyboard(),
    )


@router.message(Command("site"))
async def cmd_site(message: Message):
    user = message.from_user

    logger.info(
        f"Пользователь {user.id} ({user.username or 'no_username'}) "
        f"нажал /site"
    )

    await message.answer(
        SITE_TEXT,
        parse_mode="HTML",
        reply_markup=site_keyboard(),
    )


@router.callback_query(F.data == "get_material")
async def get_material_callback(callback: CallbackQuery):
    user = callback.from_user
    name = user.first_name or (
        f"@{user.username}" if user.username else "друг"
    )

    logger.info(f"Пользователь {user.id} нажал «Получить материал»")

    subscribed = await is_user_subscribed(user.id)

    await fade_out(callback.message)

    if subscribed:
        await send_pdf(callback.message.chat.id, name)
    else:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=NOT_SUBSCRIBED_TEXT,
            parse_mode="HTML",
            reply_markup=subscribe_keyboard(),
        )


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery):
    user = callback.from_user
    name = user.first_name or (
        f"@{user.username}" if user.username else "друг"
    )

    logger.info(f"Пользователь {user.id} нажал «Проверить подписку»")

    subscribed = await is_user_subscribed(user.id)

    if subscribed:
        await fade_out(callback.message)
        await send_pdf(callback.message.chat.id, name)
    else:
        await callback.answer(
            "❌ Подписка не найдена!",
            show_alert=True,
        )
        try:
            await callback.message.edit_text(
                STILL_NOT_SUBSCRIBED_TEXT,
                parse_mode="HTML",
                reply_markup=subscribe_keyboard(),
            )
        except Exception:
            pass


async def main():
    logger.info("🤖 Бот запускается...")

    if not os.path.exists(PDF_PATH):
        logger.error(f"❌ Файл {PDF_PATH} не найден!")
        return

    await start_fake_server()

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())