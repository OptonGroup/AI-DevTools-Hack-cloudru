import asyncio
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config.config import config
from src.handlers import router
from src.services.request_manager import request_manager


async def cleanup_task():
    """Periodically clean up old requests"""
    while True:
        await asyncio.sleep(60)
        request_manager.cleanup_old_requests()


async def main():
    bot = Bot(
        token=config.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=None),
    )
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook()

    cleanup_task_obj = asyncio.create_task(cleanup_task())

    try:
        print("🤖 Meeting Assistant Bot started")
        print(f"📡 Agent URL: {config.AGENT_API_URL}")
        await dp.start_polling(bot)
    finally:
        cleanup_task_obj.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task_obj


if __name__ == "__main__":
    try:
        print("Starting Meeting Assistant Telegram Bot...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
