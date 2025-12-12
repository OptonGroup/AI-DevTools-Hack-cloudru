import asyncio
from contextlib import asynccontextmanager, suppress
from typing import Dict, Optional, Tuple, Union

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import src.keyboards as kb
from config import config, get_config
from src.services.request_manager import request_manager
from src.utils.session import session_store

router = Router(name=__name__)

# User states storage
user_states: Dict[int, str] = {}
user_last_messages: Dict[int, Tuple[int, int]] = {}


@asynccontextmanager
async def typing_context(chat_id: int, bot: Bot, interval: float = 4.0):
    """Context manager that shows typing indicator"""
    stop_typing = asyncio.Event()

    async def typing_worker():
        while not stop_typing.is_set():
            try:
                await bot.send_chat_action(chat_id, "typing")
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception:
                break

    typing_task = asyncio.create_task(typing_worker())
    try:
        yield
    finally:
        stop_typing.set()
        typing_task.cancel()
        with suppress(asyncio.CancelledError):
            await typing_task


def create_retry_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard with retry button"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔄 Повторить", callback_data="retry_request"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_retry"))
    return builder.as_markup()


async def send_message_safe(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    reply_to_message_id: Optional[int] = None,
) -> Optional[Message]:
    """Send message with error handling"""
    try:
        # Split long messages
        if len(text) > 4096:
            chunks = [text[i : i + 4096] for i in range(0, len(text), 4096)]
            sent_msg = None
            for i, chunk in enumerate(chunks):
                markup = reply_markup if i == len(chunks) - 1 else None
                sent_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=chunk,
                    reply_markup=markup,
                    reply_to_message_id=reply_to_message_id if i == 0 else None,
                )
            return sent_msg
        else:
            return await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id,
            )
    except TelegramBadRequest as e:
        # Try without markdown if parsing fails
        try:
            return await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id,
                parse_mode=None,
            )
        except Exception:
            return None
    except Exception:
        return None


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    if not message.from_user:
        return

    user_id = message.from_user.id
    user_states[user_id] = "main_menu"

    welcome_text = """👋 Добро пожаловать в Meeting Assistant!

Я помогу вам:
• 📅 Создавать встречи в календаре
• 🎙 Подключать бота к созвонам для записи
• 🔍 Искать информацию по прошлым встречам
• 💬 Отвечать на вопросы по транскрипциям

Выберите действие:"""

    await send_message_safe(
        message.bot, message.from_user.id, welcome_text, kb.main_menu
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Return to main menu"""
    if not callback.from_user or not callback.message:
        return

    user_id = callback.from_user.id
    user_states[user_id] = "main_menu"

    await callback.message.edit_text("Главное меню:", reply_markup=kb.main_menu)
    await callback.answer()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Show help menu"""
    if not callback.from_user or not callback.message:
        return

    user_id = callback.from_user.id
    user_states[user_id] = "help_menu"

    help_text = """🆘 Помощь

После подключения к агенту вы можете:

📅 Создание встреч:
• "Создай встречу на завтра в 14:00 на час"
• "Запланируй созвон с командой в пятницу"

🎙 Подключение к созвонам:
• "Подключись к созвону https://meet.google.com/xxx"
• "Запиши встречу по ссылке [URL]"

🔍 Поиск по встречам:
• "О чём говорили на прошлой встрече?"
• "Найди упоминания бюджета"
• "Какие задачи назначили Васе?"

📋 Список созвонов:
• "Покажи последние созвоны"
• "Какие встречи были на этой неделе?"
"""

    await callback.message.edit_text(help_text, reply_markup=kb.help_menu)
    await callback.answer()


@router.callback_query(F.data == "start_work")
async def start_work(callback: CallbackQuery):
    """Show start work menu"""
    if not callback.from_user or not callback.message:
        return

    user_id = callback.from_user.id
    user_states[user_id] = "start_work_menu"

    await callback.message.edit_text(
        "Начало работы с агентом:", reply_markup=kb.start_work_menu
    )
    await callback.answer()


@router.callback_query(F.data == "connect_to_agent")
async def connect_to_agent(callback: CallbackQuery):
    """Connect to AI agent"""
    if not callback.from_user or not callback.message:
        return

    user_id = callback.from_user.id
    cfg = get_config()

    try:
        agent_url = cfg.AGENT_API_URL

        if not agent_url:
            raise ValueError("AGENT_API_URL not configured")

        session_store.connect_agent(user_id, agent_url)
        user_states[user_id] = "connected"

        await callback.message.edit_text(
            f"✅ Подключено к агенту!\n\n"
            f"• URL: {agent_url}\n"
            f"• Статус: Активен\n\n"
            f"Теперь вы можете отправлять сообщения агенту.",
            reply_markup=kb.disconnect_menu,
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка подключения: {str(e)}", reply_markup=kb.connect_cancel_menu
        )

    await callback.answer()


@router.callback_query(F.data == "cancel_connect")
async def cancel_connect(callback: CallbackQuery):
    """Cancel connection attempt"""
    if not callback.from_user or not callback.message:
        return

    user_id = callback.from_user.id
    user_states[user_id] = "start_work_menu"

    await callback.message.edit_text(
        "Подключение отменено.", reply_markup=kb.start_work_menu
    )
    await callback.answer()


@router.callback_query(F.data == "disconnect")
async def disconnect_agent(callback: CallbackQuery):
    """Disconnect from agent"""
    if not callback.from_user or not callback.message:
        return

    user_id = callback.from_user.id
    session_store.disconnect_agent(user_id)
    user_states[user_id] = "main_menu"

    await callback.message.edit_text(
        "✅ Вы отключены от агента", reply_markup=kb.main_menu
    )
    await callback.answer()


@router.callback_query(F.data == "retry_request")
async def retry_request(callback: CallbackQuery):
    """Retry failed request"""
    await callback.answer("Функция повтора в разработке")


@router.callback_query(F.data == "cancel_retry")
async def cancel_retry(callback: CallbackQuery):
    """Cancel retry"""
    if not callback.from_user or not callback.message:
        return

    await callback.message.edit_text("❌ Отменено", reply_markup=kb.main_menu)
    await callback.answer()


@router.message()
async def handle_message(message: Message):
    """Handle all text messages"""
    if not message.from_user or not message.text or not message.bot:
        return

    user_id = message.from_user.id
    bot = message.bot

    # Check if user is connected
    if user_states.get(user_id) != "connected":
        await send_message_safe(
            bot,
            user_id,
            "❌ Сначала подключитесь к агенту.\n\nНажмите /start и выберите 'Начать работу' → 'Подключиться к агенту'",
        )
        return

    agent = session_store.get_agent(user_id)
    if not agent:
        await send_message_safe(
            bot, user_id, "❌ Агент не найден. Попробуйте переподключиться."
        )
        return

    async def process_request():
        try:
            async with typing_context(user_id, bot):
                response = await agent.send_message(message.text)

                if asyncio.current_task() and asyncio.current_task().cancelled():
                    return

                await send_message_safe(
                    bot,
                    user_id,
                    response,
                    reply_to_message_id=message.message_id,
                )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            await send_message_safe(
                bot,
                user_id,
                f"❌ Ошибка: {str(e)}",
                reply_markup=create_retry_keyboard(),
                reply_to_message_id=message.message_id,
            )

    task = asyncio.create_task(process_request())
    request_manager.add_request(user_id, task)


@router.edited_message()
async def handle_edited_message(message: Message):
    """Handle edited messages"""
    if not message.from_user or not message.text or not config.HANDLE_MESSAGE_EDITS:
        return

    user_id = message.from_user.id

    if user_states.get(user_id) == "connected":
        request_manager.cancel_request(user_id)
        await handle_message(message)
