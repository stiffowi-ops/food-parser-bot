import asyncio
import os
import time

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STIFF_USER_ID = int(os.getenv("STIFF_USER_ID"))

bot = Bot(token=BOT_TOKEN)

# 🔥 ВАЖНО FIX: storage добавлен
dp = Dispatcher(storage=MemoryStorage())

requests = {}
active_requests = set()
user_last_request_time = {}

MAX_ACTIVE = 5
COOLDOWN = 24 * 60 * 60


# -----------------------
# FSM
# -----------------------
class StiffFSM(StatesGroup):
    waiting_request_id_text = State()
    waiting_file = State()
    waiting_request_id_file = State()


# -----------------------
# PANEL
# -----------------------
def panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Запрос не выполнен", callback_data="msg_fail")],
        [InlineKeyboardButton(text="❓ Информация не найдена", callback_data="msg_notfound")],
        [InlineKeyboardButton(text="⚠️ Неверная ссылка", callback_data="msg_badlink")],
        [InlineKeyboardButton(text="📦 Отправить файл", callback_data="send_file")]
    ])


# -----------------------
# START
# -----------------------
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("👋 Отправь ссылку 🌌")


# -----------------------
# PANEL FIX (ОБЯЗАТЕЛЬНО)
# -----------------------
@dp.message(Command("panel"))
async def show_panel(message: Message):
    if message.from_user.id != STIFF_USER_ID:
        return

    await message.answer("🛠 Панель", reply_markup=panel())


# -----------------------
# URL HANDLER
# -----------------------
@dp.message(F.text.startswith("http"))
async def handle_url(message: Message):

    user_id = message.from_user.id
    now = time.time()

    if user_last_request_time.get(user_id):
        if now - user_last_request_time[user_id] < COOLDOWN:
            await message.answer(
                "Не спеши, а то успеешь.\nЗвёзды любят настойчивых 🌙, но тоже устают\n Приходи через 24 часа"
            )
            return

    if len(active_requests) >= MAX_ACTIVE:
        await message.answer(
            "⚠ Перегрузка системы\nПопробуй позже 🌌"
        )
        return

    request_id = f"{user_id}_{message.message_id}"

    requests[request_id] = user_id
    active_requests.add(request_id)
    user_last_request_time[user_id] = now

    await message.answer("✔ Запрос принят...\n🌌 Ждём ответ вселенной")

    await bot.send_message(
        STIFF_USER_ID,
        f"📩 RequestID: {request_id}\nURL: {message.text}"
    )


# -----------------------
# CALLBACK TEXT ACTIONS
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

    if request_id not in requests:
        await message.answer("❌ RequestID не найден")
        await state.clear()
        return

    user_id = requests[request_id]
    data = await state.get_data()

    texts = {
        "msg_fail": "❌ Твой запрос не выполнен",
        "msg_notfound": "❓ Информация не найдена",
        "msg_badlink": "⚠️ Ссылка не соответствует формату"
    }

    await bot.send_message(user_id, texts.get(data["action"], "Ответ"))

    active_requests.discard(request_id)

    await message.answer("✔ Отправлено")
    await state.clear()


# -----------------------
# FILE FLOW FIX
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

    await message.answer("✔ Файл отправлен")
    await state.clear()


# -----------------------
# RUN
# -----------------------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
