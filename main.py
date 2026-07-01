import asyncio
import os
import time

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STIFF_USER_ID = int(os.getenv("STIFF_USER_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# -----------------------
# STORAGE
# -----------------------
requests = {}
user_last_request_time = {}
active_requests = set()

MAX_ACTIVE_REQUESTS = 5
COOLDOWN_SECONDS = 24 * 60 * 60


# -----------------------
# TEXTS
# -----------------------
TEXT_COOLDOWN = (
    "Не спеши, а то успеешь.\n"
    "Звёзды любят настойчивых, но тоже устают 🌙\n\n"
    "Попробуй снова через 24 часа."
)

TEXT_OVERLOAD = (
    "⚠ Сейчас слишком много запросов во Вселенной.\n\n"
    "Мы не можем принять новый сигнал 🌌\n\n"
    "Попробуй позже — как только освободится место, портал снова откроется."
)

TEXT_OK = (
    "✔ Запрос принят...\n\n"
    "🌌 Ждём ответ вселенной"
)


# -----------------------
# START
# -----------------------
@dp.message(F.text == "/start")
async def start(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(1)

    await message.answer(
        "👋 Привет!\n\n"
        "Отправь ссылку (URL), и я передам её оператору.\n"
        "🌌 Вселенная иногда отвечает не сразу..."
    )


# -----------------------
# URL HANDLER
# -----------------------
@dp.message(F.text.startswith("http"))
async def handle_url(message: Message):

    user_id = message.from_user.id
    now = time.time()

    # -----------------------
    # 1. COOLDOWN CHECK
    # -----------------------
    last_time = user_last_request_time.get(user_id)

    if last_time and now - last_time < COOLDOWN_SECONDS:
        await message.answer(TEXT_COOLDOWN)
        return

    # -----------------------
    # 2. LOAD LIMIT CHECK
    # -----------------------
    if len(active_requests) >= MAX_ACTIVE_REQUESTS:
        await message.answer(TEXT_OVERLOAD)
        return

    # -----------------------
    # 3. REGISTER REQUEST
    # -----------------------
    request_id = f"{user_id}_{message.message_id}"

    requests[request_id] = user_id
    active_requests.add(request_id)
    user_last_request_time[user_id] = now

    # -----------------------
    # 4. UX RESPONSE
    # -----------------------
    loading = await message.answer("⏳ Инициализация запроса...")
    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(1.5)

    await loading.edit_text(TEXT_OK)

    # -----------------------
    # 5. SEND TO STIFF
    # -----------------------
    await bot.send_message(
        chat_id=STIFF_USER_ID,
        text=(
            "📩 Новый запрос\n\n"
            f"RequestID: {request_id}\n"
            f"URL: {message.text}\n\n"
            "📌 Ответь файлом с этим RequestID"
        )
    )


# -----------------------
# FILE FROM STIFF
# -----------------------
@dp.message(F.document)
async def handle_file(message: Message):

    if message.from_user.id != STIFF_USER_ID:
        return

    if not message.caption:
        await message.answer("⚠ Укажи RequestID в подписи")
        return

    request_id = message.caption.strip()

    if request_id not in requests:
        await message.answer("❌ RequestID не найден")
        return

    user_id = requests[request_id]

    # освобождаем слот
    active_requests.discard(request_id)

    await bot.send_document(
        chat_id=user_id,
        document=message.document.file_id,
        caption="📦 Ваш ответ готов"
    )

    await message.answer("✔ Файл доставлен пользователю")


# -----------------------
# RUN
# -----------------------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
