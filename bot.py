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
from aiogram.filters import CommandStart, CommandObject
from aiogram.enums import ChatMemberStatus
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Конфигурация
# ─────────────────────────────────────────────
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_URL = os.getenv("CHANNEL_URL")

PDF_PATH = os.path.join("files", "checklist.pdf")

# ─────────────────────────────────────────────
# Логирование
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Инициализация
# ─────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ─────────────────────────────────────────────
# Тексты
# ─────────────────────────────────────────────

WELCOME_TEXT = (
    "👋 Привет, <b>{name}</b>!\n"
    "\n"
    "Рад видеть тебя здесь!\n"
    "\n"
    "🎁 У меня для тебя <b>бесплатный подарок</b>:\n"
    "\n"
    "📋 <b>«Чек-лист ТОП-10 ошибок, которые убивают\n"
    "конверсию вашего сайта»</b>\n"
    "\n"
    "Нажми кнопку ниже, чтобы получить его 👇"
)

NOT_SUBSCRIBED_TEXT = (
    "😔 Ты пока <b>не подписан</b> на наш канал.\n"
    "\n"
    "Подпишись на канал и нажми\n"
    "<b>«🔄 Проверить подписку»</b> 👇"
)

SUCCESS_TEXT = (
    "🎉 Отлично, <b>{name}</b>!\n"
    "\n"
    "Подписка подтверждена ✅\n"
    "\n"
    "Держи свой подарок 👇\n"
    "\n"
    "📋 <b>«Чек-лист ТОП-10 ошибок, которые убивают\n"
    "конверсию вашего сайта»</b>\n"
    "\n"
    "Изучай, внедряй и увеличивай конверсию! 🚀"
)

STILL_NOT_SUBSCRIBED_TEXT = (
    "🤔 Подписки всё ещё нет…\n"
    "\n"
    "Убедись, что ты нажал <b>«Подписаться»</b>\n"
    "в канале, а потом нажми\n"
    "<b>«🔄 Проверить подписку»</b> ещё раз 👇"
)


# ─────────────────────────────────────────────
# Клавиатуры
# ─────────────────────────────────────────────

def welcome_keyboard() -> InlineKeyboardMarkup:
    """Стартовая клавиатура с кнопкой получения материала."""
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
    """Клавиатура: перейти на канал + проверить подписку."""
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


# ─────────────────────────────────────────────
# Проверка подписки
# ─────────────────────────────────────────────

async def is_user_subscribed(user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на канал."""
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


# ─────────────────────────────────────────────
# Отправка PDF
# ─────────────────────────────────────────────

async def send_pdf(callback: CallbackQuery, name: str):
    """Удаляет старое сообщение и отправляет PDF."""
    # Удаляем сообщение с кнопками
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Текст успеха
    await callback.message.answer(
        SUCCESS_TEXT.format(name=name),
        parse_mode="HTML",
    )

    # Отправляем PDF
    document = FSInputFile(
        PDF_PATH,
        filename="Чек-лист_ТОП-10_ошибок_конверсии.pdf",
    )
    await callback.message.answer_document(
        document=document,
        caption="📎 Твой чек-лист готов. Приятного изучения!",
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────
# Хэндлер /start
# ─────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user = message.from_user
    name = user.first_name or (f"@{user.username}" if user.username else "друг")
    source = command.args

    logger.info(
        f"Пользователь {user.id} ({user.username or 'no_username'}) "
        f"нажал /start (source={source})"
    )

    await message.answer(
        WELCOME_TEXT.format(name=name),
        parse_mode="HTML",
        reply_markup=welcome_keyboard(),
    )


# ─────────────────────────────────────────────
# Кнопка «Получить материал»
# ─────────────────────────────────────────────

@router.callback_query(F.data == "get_material")
async def get_material_callback(callback: CallbackQuery):
    user = callback.from_user
    name = user.first_name or (f"@{user.username}" if user.username else "друг")

    logger.info(f"Пользователь {user.id} нажал «Получить материал»")

    # Проверяем подписку
    subscribed = await is_user_subscribed(user.id)

    if subscribed:
        # Подписан — выдаём PDF
        await send_pdf(callback, name)
    else:
        # Не подписан — просим подписаться
        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            NOT_SUBSCRIBED_TEXT,
            parse_mode="HTML",
            reply_markup=subscribe_keyboard(),
        )


# ─────────────────────────────────────────────
# Кнопка «Проверить подписку»
# ─────────────────────────────────────────────

@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery):
    user = callback.from_user
    name = user.first_name or (f"@{user.username}" if user.username else "друг")

    logger.info(f"Пользователь {user.id} нажал «Проверить подписку»")

    subscribed = await is_user_subscribed(user.id)

    if subscribed:
        # Подписался — выдаём PDF
        await send_pdf(callback, name)
    else:
        # Всё ещё не подписан
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


# ─────────────────────────────────────────────
# Запуск
# ─────────────────────────────────────────────

async def main():
    logger.info("🤖 Бот запускается...")

    if not os.path.exists(PDF_PATH):
        logger.error(f"❌ Файл {PDF_PATH} не найден!")
        return

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Бот запущен и готов к работе!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())