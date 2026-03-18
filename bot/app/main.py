import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.api_client import client
from app.config import settings
from app.handlers.balance import router as balance_router
from app.handlers.contact import router as contact_router
from app.handlers.start import router as start_router
from app.worker import stream_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(balance_router)
    dp.include_router(contact_router)

    worker_task = asyncio.create_task(stream_worker(bot))

    logger.info("Бот запущен.")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        worker_task.cancel()
        await asyncio.gather(worker_task, return_exceptions=True)
        await client.aclose()
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
