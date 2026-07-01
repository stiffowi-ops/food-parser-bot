import asyncio
import os
import time

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
active_requests = set()
user_last_request_time = {}

MAX_ACTIVE = 5
COOLDOWN = 24 * 60 * 60


# -----------------------
# STATES
# -----------------------
class StiffFSM(StatesGroup):
    waiting_request_id_text = State()
    waiting_file = State()
    waiting_request_id_file = State()


# -----------------------
# PANEL BUTTONS
# -----------------------
def stiff_panel():
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

    await message.answer(
        "👋 Привет!\n\nОтправь ссылку, и я обработаю её 🌌"
    )


# -----------------------
# USER URL
# -----------------------
@dp.message(F.text.startswith("http"))
async def handle_url(message: Message):

    user_id = message.from_user.id
    now = time.time()

    # cooldown
    if user_last_request_time.get(user_id):
        if now - user_last_request_time[user_id] < COOLDOWN:
            await message.answer(
                "Не спеши, а то успеешь.\n"
                "Звёзды любят настойчивых, но тоже устают 🌙"
            )
            return

    # limit
    if len(active_requests) >= MAX_ACTIVE:
        await message.answer(
            "⚠ Сейчас слишком много запросов во Вселенной.\n"
            "Попробуй позже 🌌"
        )
        return

    request_id = f"{user_id}_{message.message_id}"

    requests[request_id] = user_id
    active_requests.add(request_id)
    user_last_request_time[user_id] = now

    await message.answer("✔ Запрос принят...\n🌌 Ждём ответ вселенной")

    await bot.send_message(
        STIFF_USER_ID,
        f"📩 Новый запрос\nRequestID: {request_id}\nURL: {message.text}"
    )


# =========================================================
# STIFF PANEL CALLBACKS (TEXT RESPONSES)
# =========================================================

@dp.message(Command("panel"))
async def panel(message: Message):
    if message.from_user.id != STIFF_USER_ID:
        return

    await message.answer("🛠 Панель управления", reply_markup=stiff_panel())


# -----------------------
# STEP 1 - choose action
# -----------------------
@dp.callback_query(F.data.startswith("msg_"))
async def handle_msg_buttons(callback: CallbackQuery, state: FSMContext):

    if callback.from_user.id != STIFF_USER_ID:
        return

    await state.update_data(action=callback.data)

    await state.set_state(StiffFSM.waiting_request_id_text)

    await callback.message.answer("✏ Введите RequestID:")
    await callback.answer()


# -----------------------
# STEP 2 - send text response
# -----------------------
@dp.message(StiffFSM.waiting_request_id_text)
async def send_text_response(message: Message, state: FSMContext):

    request_id = message.text.strip()

    if request_id not in requests:
        await message.answer("❌ RequestID не найден")
        await state.clear()
        return

    user_id = requests[request_id]
    data = await state.get_data()

    action = data.get("action")

    texts = {
        "msg_fail": "❌ Твой запрос не выполнен",
        "msg_notfound": "❓ Информация не найдена",
        "msg_badlink": "⚠️ Ссылка не соответствует формату, попробуй снова"
    }

    await bot.send_message(user_id, texts.get(action, "Ответ от оператора"))

    active_requests.discard(request_id)

    await message.answer("✔ Ответ отправлен пользователю")
    await state.clear()


# =========================================================
# FILE FLOW
# =========================================================

@dp.callback_query(F.data == "send_file")
async def send_file_start(callback: CallbackQuery, state: FSMContext):

    if callback.from_user.id != STIFF_USER_ID:
        return

    await state.set_state(StiffFSM.waiting_file)

    await callback.message.answer("📎 Отправьте файл:")
    await callback.answer()


@dp.message(StiffFSM.waiting_file, F.document)
async def receive_file(message: Message, state: FSMContext):

    await state.update_data(file_id=message.document.file_id)

    await state.set_state(StiffFSM.waiting_request_id_file)

    await message.answer("✏ Теперь введите RequestID:")


@dp.message(StiffFSM.waiting_request_id_file)
async def confirm_send_file(message: Message, state: FSMContext):

    request_id = message.text.strip()

    if request_id not in requests:
        await message.answer("❌ RequestID не найден")
        await state.clear()
        return

    data = await state.get_data()
    file_id = data["file_id"]

    user_id = requests[request_id]

    await bot.send_document(
        chat_id=user_id,
        document=file_id,
        caption="📦 Файл от оператора"
    )

    active_requests.discard(request_id)

    await message.answer("✔ Файл отправлен пользователю")
    await state.clear()


# -----------------------
# RUN
# -----------------------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
