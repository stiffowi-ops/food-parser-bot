import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from dotenv import load_dotenv

# -----------------------
# ENV
# -----------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STIFF_USER_ID = int(os.getenv("STIFF_USER_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# хранение заявок
requests = {}


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
        "🌌 Ждём ответ вселенной..."
    )


# -----------------------
# URL -> ОПЕРАТОРУ
# -----------------------
@dp.message(F.text.startswith("http"))
async def handle_url(message: Message):

    user_id = message.from_user.id
    url = message.text

    request_id = f"{user_id}_{message.message_id}"
    requests[request_id] = user_id

    # 1) сразу показываем загрузку (без циклов!)
    loading = await message.answer("⏳ Инициализация запроса...")

    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(1.5)

    # 2) одно обновление текста (без повторов → нет ошибки TelegramBadRequest)
    await loading.edit_text("✔ Запрос отправлен...\n🌌 Ждём ответ вселенной")

    # 3) отправляем только Stiff
    await bot.send_message(
        chat_id=STIFF_USER_ID,
        text=(
            "📩 Новый запрос\n\n"
            f"RequestID: {request_id}\n"
            f"URL: {url}\n\n"
            "📌 Ответь файлом с этим RequestID в подписи"
        )
    )


# -----------------------
# ФАЙЛ ОТ STIFF
# -----------------------
@dp.message(F.document)
async def handle_file(message: Message):

    # защита: только Stiff
    if message.from_user.id != STIFF_USER_ID:
        await message.answer("⛔ Нет доступа")
        return

    if not message.caption:
        await message.answer("⚠ Укажи RequestID в подписи к файлу")
        return

    request_id = message.caption.strip()

    if request_id not in requests:
        await message.answer("❌ RequestID не найден")
        return

    user_id = requests[request_id]

    # эффект загрузки перед отправкой
    await bot.send_chat_action(user_id, "upload_document")
    await asyncio.sleep(1)

    await bot.send_document(
        chat_id=user_id,
        document=message.document.file_id,
        caption="📦 Ваш файл готов"
    )

    await message.answer("✔ Файл доставлен пользователю")


# -----------------------
# RUN
# -----------------------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
