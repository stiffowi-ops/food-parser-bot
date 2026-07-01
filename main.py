import asyncio
import os
import time
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# -----------------------
# ENV
# -----------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STIFF_USER_ID = int(os.getenv("STIFF_USER_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# -----------------------
# DB
# -----------------------
conn = sqlite3.connect("bot.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS requests (
    request_id TEXT PRIMARY KEY,
    user_id INTEGER,
    status TEXT,
    created_at REAL
)
""")

conn.commit()

# -----------------------
# STATES
# -----------------------
class StiffFSM(StatesGroup):
    waiting_request_id_text = State()
    waiting_file = State()
    waiting_request_id_file = State()

# -----------------------
# TEXTS (ВОЗВРАЩЕНЫ 💫)
# -----------------------
TEXT_START = (
    "👋 Привет!\n\n"
    "Отправь ссылку (URL), и я передам её до востребования 🌌"
)

TEXT_OK = (
    "✔ Запрос принят...\n\n"
    "🌌 Ждём ответ вселенной"
)

TEXT_COOLDOWN = (
    "Не спеши, а то успеешь.\n"
    "Звёзды любят настойчивых, но тоже устают 🌙\n\n"
    "Попробуй снова через 24 часа."
)

TEXT_OVERLOAD = (
    "⚠ Сейчас слишком много запросов во Вселенной.\n\n"
    "Портал перегружен 🌌\n"
    "Попробуй позже — как только освободится место, он снова откроется."
)

# -----------------------
# DB HELPERS
# -----------------------
def save_request(request_id, user_id):
    cur.execute(
        "INSERT OR REPLACE INTO requests VALUES (?, ?, ?, ?)",
        (request_id, user_id, "active", time.time())
    )
    conn.commit()


def get_request(request_id):
    cur.execute("SELECT user_id FROM requests WHERE request_id=?", (request_id,))
    return cur.fetchone()


def close_request(request_id):
    cur.execute("UPDATE requests SET status='done' WHERE request_id=?", (request_id,))
    conn.commit()


def active_count():
    cur.execute("SELECT COUNT(*) FROM requests WHERE status='active'")
    return cur.fetchone()[0]


# -----------------------
# PANEL
# -----------------------
def panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Твой запрос не выполнен", callback_data="msg_fail")],
        [InlineKeyboardButton(text="❓ Информация не найдена", callback_data="msg_notfound")],
        [InlineKeyboardButton(text="⚠️ Ссылка не соответствует формату", callback_data="msg_badlink")],
        [InlineKeyboardButton(text="📦 Отправить файл", callback_data="send_file")]
    ])


# -----------------------
# START
# -----------------------
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(TEXT_START)


# -----------------------
# PANEL
# -----------------------
@dp.message(Command("panel"))
async def show_panel(message: Message):
    if message.from_user.id != STIFF_USER_ID:
        return

    await message.answer("🛠 Панель управления", reply_markup=panel())


# -----------------------
# URL HANDLER
# -----------------------
@dp.message(F.text.startswith("http"))
async def handle_url(message: Message):

    user_id = message.from_user.id

    if active_count() >= 5:
        await message.answer(TEXT_OVERLOAD)
        return

    request_id = f"{user_id}_{message.message_id}"

    save_request(request_id, user_id)

    await message.answer(TEXT_OK)

    await bot.send_message(
        STIFF_USER_ID,
        f"📩 Новый запрос\n\nRequestID: {request_id}\nURL: {message.text}"
    )


# -----------------------
# TEXT CALLBACKS
# -----------------------
@dp.callback_query(F.data.startswith("msg_"))
async def text_action(callback: CallbackQuery, state: FSMContext):

    if callback.from_user.id != STIFF_USER_ID:
        return

    await state.update_data(action=callback.data)
    await state.set_state(StiffFSM.waiting_request_id_text)

    await callback.message.answer("✏ Введите RequestID:")
    await callback.answer()


@dp.message(StiffFSM.waiting_request_id_text)
async def send_text(message: Message, state: FSMContext):

    request_id = message.text.strip()

    row = get_request(request_id)

    if not row:
        await message.answer("❌ RequestID не найден")
        await state.clear()
        return

    user_id = row[0]
    action = (await state.get_data())["action"]

    texts = {
        "msg_fail": "❌ Твой запрос не выполнен",
        "msg_notfound": "❓ Информация не найдена",
        "msg_badlink": "⚠️ Ссылка не соответствует формату, попробуй снова"
    }

    await bot.send_message(user_id, texts.get(action, "Ответ оператора"))

    close_request(request_id)

    await message.answer("✔ Ответ отправлен")
    await state.clear()


# -----------------------
# FILE FLOW
# -----------------------
@dp.callback_query(F.data == "send_file")
async def file_start(callback: CallbackQuery, state: FSMContext):

    if callback.from_user.id != STIFF_USER_ID:
        return

    await state.set_state(StiffFSM.waiting_file)

    await callback.message.answer("📎 Отправьте файл:")
    await callback.answer()


@dp.message(StiffFSM.waiting_file, F.document)
async def file_received(message: Message, state: FSMContext):

    await state.update_data(file_id=message.document.file_id)
    await state.set_state(StiffFSM.waiting_request_id_file)

    await message.answer("✏ Введите RequestID:")


@dp.message(StiffFSM.waiting_request_id_file)
async def file_send(message: Message, state: FSMContext):

    request_id = message.text.strip()

    row = get_request(request_id)

    if not row:
        await message.answer("❌ RequestID не найден")
        await state.clear()
        return

    user_id = row[0]
    file_id = (await state.get_data())["file_id"]

    await bot.send_document(
        chat_id=user_id,
        document=file_id,
        caption="📦 Ответ доставлен\n\nИногда вселенная отвечает не словами, а файлами 🌙"
    )

    close_request(request_id)

    await message.answer("✔ Файл отправлен")
    await state.clear()


# -----------------------
# RUN
# -----------------------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
