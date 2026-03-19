import asyncio
import aiohttp

async def check_updates(token, name):
    print(f"Checking updates for {name} ({token[:10]}...)")
    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{token}/getUpdates?offset=-1&limit=5"
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                print(f"Result for {name}: {data}")
        except Exception as e:
            print(f"Failed for {name}: {e}")

async def main():
    t1 = "8548893916:AAEYCfuTDuwNLoD1I59cfePucHyBaFWb0ug" # Andijon
    t2 = "8718577205:AAFsElRRL9sTXKF4hQF9yqwOogM_2KQUSLo" # Toshkent
    await check_updates(t1, "Andijon_Bot")
    await check_updates(t2, "Toshkent_Bot")

if __name__ == "__main__":
    asyncio.run(main())
