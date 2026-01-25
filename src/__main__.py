import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config import BOT_TOKEN, USE_MOCK_API
from src.handlers import start, menu_message, settings_handlers, order_handlers
from src.services.order_monitor import start_monitoring
from src.checkpoint_manager import init_checkpointer, close_checkpointer
from src.db.database import init_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # Initialize database
    init_database()
    logger.info("✅ Database initialized")

    # Log mock mode status
    if USE_MOCK_API:
        logger.info("⚠️ MOCK MODE ENABLED - Using fake data for testing")
    else:
        logger.info("📡 Using real API")

    # Initialize checkpointer for workflow state persistence
    await init_checkpointer()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(menu_message.router)
    dp.include_router(settings_handlers.router)
    dp.include_router(order_handlers.router)

    # Запуск мониторинга заказов
    asyncio.create_task(start_monitoring(bot))

    # Send mock orders on startup if in mock mode
    if USE_MOCK_API:
        from src.services.mock_startup import send_mock_orders_on_startup
        asyncio.create_task(send_mock_orders_on_startup(bot))

    logger.info("🚀 Bot started!")

    try:
        await dp.start_polling(bot)
    finally:
        await close_checkpointer()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹ Bot stopped!")
