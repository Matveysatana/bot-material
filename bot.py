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
from aiogram.filters import CommandStart
from aiogram.enums import ChatMemberStatus
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Конфигурация
# ─────────────────────────────────────────────
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")       # @username или -100...
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
# Тексты (вынесены отдельно для удобства)
# ─────────────────────────────────────────────

WELCOME_TEXT = (
    "👋 Привет, <b>{name}</b>!\n"
    "\n"
    "Рад видеть тебя здесь!\n"
    "\n"
    "🎁 У меня для тебя <b>бесплатный подарок</b>:\n"
    "📋 <b>«Чек-лист ТОП-10 ошибок, которые убивают конверсию вашего сайта»</b>\n"
    "\n"
    "Чтобы получить его — нужно быть подписанным на наш канал.\n"
    "Сейчас проверю… ⏳"
)

NOT_SUBSCRIBED_TEXT = (
    "😔 Ты пока <b>не подписан</b> на наш канал.\n"
    "\n"
    "Подпишись 👇 и нажми <b>«✅ Я подписался»</b>, чтобы получить чек-лист!"
)

ALREADY_SUBSCRIBED_TEXT = (
    "🎉 Отлично, <b>{name}</b>! Ты подписан на канал!\n"
    "\n"
    "Держи свой подарок 👇\n"
    "\n"
    "📋 <b>«Чек-лист ТОП-10 ошибок, которые убивают конверсию вашего сайта»</b>\n"
    "\n"
    "Изучай, внедряй и увеличивай конверсию! 🚀"
)

CHECK_SUCCESS_TEXT = (
    "🎉 Супер, <b>{name}</b>! Подписка подтверждена!\n"
    "\n"
    "Вот твой чек-лист 👇\n"
    "\n"
    "📋 <b>«ТОП-10 ошибок, которые убивают конверсию вашего сайта»</b>\n"
    "\n"
    "Применяй и наблюдай за ростом показателей! 📈"
)

CHECK_FAIL_TEXT = (
    "🤔 Хм, подписки всё ещё нет…\n"
    "\n"
    "Убедись, что ты нажал <b>«Join»</b> / <b>«Подписаться»</b> в канале,\n"
    "а потом снова нажми <b>«✅ Я подписался»</b>."
)


# ─────────────────────────────────────────────
# Клавиатуры
# ─────────────────────────────────────────────

def get_subscribe_keyboard() -> InlineKeyboardMarkup:
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
                    text="✅ Я подписался",
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
        # Статусы, которые считаем «подписан»
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

async def send_pdf(message_or_callback, user_name: str):
    """Отправляет PDF-файл пользователю."""

    # Определяем, откуда пришёл вызов
    if isinstance(message_or_callback, CallbackQuery):
        chat_id = message_or_callback.message.chat.id
        send = message_or_callback.message.answer_document
        send_text = message_or_callback.message.answer
    else:
        chat_id = message_or_callback.chat.id
        send = message_or_callback.answer_document
        send_text = message_or_callback.answer

    # Формируем текст
    if isinstance(message_or_callback, CallbackQuery):
        text = CHECK_SUCCESS_TEXT.format(name=user_name)
    else:
        text = ALREADY_SUBSCRIBED_TEXT.format(name=user_name)

    # Отправляем текст
    await send_text(text, parse_mode="HTML")

    # Отправляем файл
    document = FSInputFile(PDF_PATH, filename="Чек-лист_ТОП-10_ошибок_конверсии.pdf")
    await send(
        document=document,
        caption="📎 Твой чек-лист готов. Приятного изучения!",
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────
# Хэндлер /start
# ─────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    # Берём имя: first_name, а если нет — username, а если нет — "друг"
    name = user.first_name or (f"@{user.username}" if user.username else "друг")

    logger.info(
        f"Пользователь {user.id} ({user.username or 'no_username'}) нажал /start"
    )

    # Приветствие
    await message.answer(
        WELCOME_TEXT.format(name=name),
        parse_mode="HTML",
    )

    # Небольшая пауза для эффекта «проверки»
    await asyncio.sleep(1.5)

    # Проверяем подписку
    subscribed = await is_user_subscribed(user.id)

    if subscribed:
        await send_pdf(message, name)
    else:
        await message.answer(
            NOT_SUBSCRIBED_TEXT,
            parse_mode="HTML",
            reply_markup=get_subscribe_keyboard(),
        )


# ─────────────────────────────────────────────
# Хэндлер кнопки «Я подписался»
# ─────────────────────────────────────────────

@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery):
    user = callback.from_user
    name = user.first_name or (f"@{user.username}" if user.username else "друг")

    logger.info(
        f"Пользователь {user.id} ({user.username or 'no_username'}) "
        f"нажал «Я подписался»"
    )

    subscribed = await is_user_subscribed(user.id)

    if subscribed:
        # Удаляем старое сообщение с кнопками
        await callback.message.delete()
        # Отправляем PDF
        await send_pdf(callback, name)
    else:
        await callback.answer(
            "❌ Подписка не найдена. Подпишись на канал!",
            show_alert=True,
        )
        # Обновляем сообщение (на случай если текст изменился)
        await callback.message.edit_text(
            CHECK_FAIL_TEXT,
            parse_mode="HTML",
            reply_markup=get_subscribe_keyboard(),
        )


# ─────────────────────────────────────────────
# Запуск
# ─────────────────────────────────────────────

async def main():
    logger.info("🤖 Бот запускается...")

    # Проверяем, что PDF на месте
    if not os.path.exists(PDF_PATH):
        logger.error(f"❌ Файл {PDF_PATH} не найден! Положи PDF в папку files/")
        return

    # Удаляем вебхук (на случай если был) и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Бот запущен и готов к работе!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())