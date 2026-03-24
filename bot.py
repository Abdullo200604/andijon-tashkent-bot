import os
import socket
import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

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
    dp.include_router(start.router)      # Start va umumiy handlerlar (Kabinet, Logout) birinchi bo'lishi kerak
    dp.include_router(orders.router)
    dp.include_router(taxi.router)
    dp.include_router(client.router)

    logging.info("🚀 Botlar ishga tushmoqda...")

    # Ikkala bot uchun ham ulanishni tekshirish va ma'lumotlarni sozlash
    for bot in [bot1, bot2]:
        for attempt in range(3):
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                
                # Bot ma'lumotlarini sozlash
                try:
                    await bot.set_my_name("Andijon Toshkent Taxi 🚕")
                    await bot.set_my_description(
                        "Andijon va Toshkent yo'nalishi bo'yicha eng tezkor taksi botiga xush kelibsiz! \n\n"
                        "Bu yerda siz: \n"
                        "✅ Mijoz sifatida buyurtma berishingiz \n"
                        "✅ Taxi haydovchisi sifatida e'lon qoldirishingiz mumkin. \n\n"
                        "Xizmat mutlaqo xavfsiz va tezkor!"
                    )
                    await bot.set_my_short_description("Andijon-Tashkent yo'nalishidagi eng zo'r taksi boti! 🚖")
                except Exception as e:
                    logging.warning(f"Name/Description sozlashda xato (e'tiborsiz qoldiriladi): {e}")

                logging.info(f"✅ Telegram API bilan ulanish o'rnatildi (Bot ID: {bot.id})")
                break
            except Exception as e:
                logging.warning(f"⚠️ Ulanishda xato (Bot ID: {bot.id}, urinish {attempt+1}/3): {e}")
                if attempt < 2:
                    await asyncio.sleep(5)
                else:
                    logging.error(f"❌ Bot ID: {bot.id} ulanib bo'lmadi.")

    # Render uchun kichik web-server (Render portni eshitishni talab qiladi)
    async def handle(request):
        return web.Response(text="Bot is running!")

    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 8080)))
    await site.start()
    logging.info(f"🌐 Web server ishga tushdi (Port: {os.getenv('PORT', 8080)})")

    try:
        await dp.start_polling(bot1, bot2)
    finally:
        await bot1.session.close()
        await bot2.session.close()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
