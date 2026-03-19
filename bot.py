import asyncio
import logging

import socket
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from config import BOT_TOKEN_1, BOT_TOKEN_2
from database import init_db
from handlers import start, client, orders, taxi, subscription, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main():
    # Bazani ishga tushirish
    await init_db()
    logging.info("✅ Ma'lumotlar bazasi tayyor.")

    # Botlarni sozlash
    default_props = DefaultBotProperties(parse_mode=ParseMode.HTML)
    bot1 = Bot(token=BOT_TOKEN_1, default=default_props)
    bot2 = Bot(token=BOT_TOKEN_2, default=default_props)

    dp = Dispatcher(storage=MemoryStorage())

    # Debug: Barcha xabarlarni log qilish uchun middleware
    @dp.update.outer_middleware()
    async def log_everything(handler, event, data):
        if event.message:
            bot_id = data['bot'].id
            chat = event.message.chat
            logging.info(f"📩 [Bot ID:{bot_id}] Yangi xabar: ChatID={chat.id}, Type={chat.type}, Text={event.message.text}")
        return await handler(event, data)

    # Routerlarni tartib bilan ulash
    dp.include_router(admin.router)
    dp.include_router(subscription.router)
    dp.include_router(orders.router)
    dp.include_router(taxi.router)
    dp.include_router(client.router)
    dp.include_router(start.router)

    logging.info("🚀 Botlar ishga tushmoqda...")

    # Ikkala bot uchun ham ulanishni tekshirish
    for bot in [bot1, bot2]:
        for attempt in range(3):
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                logging.info(f"✅ Telegram API bilan ulanish o'rnatildi (Bot ID: {bot.id})")
                break
            except Exception as e:
                logging.warning(f"⚠️ Ulanishda xato (Bot ID: {bot.id}, urinish {attempt+1}/3): {e}")
                if attempt < 2:
                    await asyncio.sleep(5)
                else:
                    logging.error(f"❌ Bot ID: {bot.id} ulanib bo'lmadi.")

    try:
        await dp.start_polling(bot1, bot2)
    finally:
        await bot1.session.close()
        await bot2.session.close()


if __name__ == "__main__":
    asyncio.run(main())
