import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STIFF_USER_ID = int(os.getenv("STIFF_USER_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

requests = {}

@dp.message(F.text == "/start")
async def start(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(1)

    await message.answer(
        "👋 Привет!\n\n"
        "Отправь ссылку (URL), и я передам её оператору.\n"
        "🌌 Ждём ответ вселенной..."
    )

@dp.message(F.text.startswith("http"))
async def handle_url(message: Message):

    user_id = message.from_user.id
    url = message.text

    request_id = f"{user_id}_{message.message_id}"
    requests[request_id] = user_id

    loading = await message.answer("⏳ Инициализация...")

    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(1)

    for _ in range(3):
        await asyncio.sleep(0.5)
        await loading.edit_text("⏳ Обработка запроса...")

    await bot.send_message(
        chat_id=STIFF_USER_ID,
        text=f"📩 RequestID: {request_id}\nURL: {url}"
    )

    await loading.edit_text(
        "✔ Запрос отправлен...\n"
        "🌌 Ждём ответ вселенной"
    )

@dp.message(F.document)
async def handle_file(message: Message):

    if message.from_user.id != STIFF_USER_ID:
        return

    if not message.caption:
        await message.answer("Укажи RequestID в подписи")
        return

    request_id = message.caption.strip()

    if request_id not in requests:
        await message.answer("RequestID не найден")
        return

    user_id = requests[request_id]

    await bot.send_document(
        chat_id=user_id,
        document=message.document.file_id,
        caption="📦 Готово"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())