import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    FSInputFile,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from config import TELEGRAM_BOT_TOKEN
from services import ai_service, docx_service, pptx_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# --- Asosiy menyu ---
MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❓ Savolga javob")],
        [KeyboardButton(text="📄 Referat tayyorlash")],
        [KeyboardButton(text="📊 Prezentatsiya tayyorlash")],
        [KeyboardButton(text="🏠 Bosh menyu")],
    ],
    resize_keyboard=True,
)

CANCEL_TEXT = "🏠 Bosh menyu"


class BotStates(StatesGroup):
    waiting_question = State()
    waiting_referat_topic = State()
    waiting_presentation_topic = State()
    waiting_slide_count = State()


# ---------------------------------------------------------------------------
# /start va bosh menyu
# ---------------------------------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "Men AI yordamchi botman. Men quyidagilarni qila olaman:\n\n"
        "❓ <b>Savolga javob</b> — istalgan savolingizga AI orqali javob beraman\n"
        "📄 <b>Referat tayyorlash</b> — mavzu bo'yicha tayyor Word (.docx) referat\n"
        "📊 <b>Prezentatsiya tayyorlash</b> — mavzu bo'yicha tayyor PowerPoint (.pptx)\n\n"
        "Quyidagi menyudan kerakli bo'limni tanlang 👇",
        reply_markup=MAIN_MENU,
    )


@router.message(F.text == CANCEL_TEXT)
async def go_home(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bosh menyu 👇", reply_markup=MAIN_MENU)


# ---------------------------------------------------------------------------
# 1) Savol-javob bo'limi
# ---------------------------------------------------------------------------
@router.message(F.text == "❓ Savolga javob")
async def start_qa(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_question)
    await message.answer(
        "Savolingizni yozing, men AI yordamida javob beraman.\n"
        "Bosh menyuga qaytish uchun \"🏠 Bosh menyu\" tugmasini bosing.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=CANCEL_TEXT)]], resize_keyboard=True
        ),
    )


@router.message(BotStates.waiting_question)
async def handle_question(message: Message, state: FSMContext):
    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        answer = ai_service.ask_question(message.text)
    except Exception as e:
        logger.exception("AI xatolik")
        await message.answer(f"❌ Xatolik yuz berdi: {e}")
        return
    # Telegram xabar uzunligi cheklovi (4096) uchun bo'lib yuborish
    for chunk in _split_text(answer, 4000):
        await message.answer(chunk)


# ---------------------------------------------------------------------------
# 2) Referat tayyorlash bo'limi
# ---------------------------------------------------------------------------
@router.message(F.text == "📄 Referat tayyorlash")
async def start_referat(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_referat_topic)
    await message.answer(
        "Referat mavzusini yozing.\nMasalan: <i>\"Sun'iy intellektning ta'lim sohasidagi ahamiyati\"</i>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=CANCEL_TEXT)]], resize_keyboard=True
        ),
    )


@router.message(BotStates.waiting_referat_topic)
async def handle_referat_topic(message: Message, state: FSMContext):
    mavzu = message.text.strip()
    await message.answer("⏳ Referat tayyorlanmoqda, bu biroz vaqt olishi mumkin...")
    await message.bot.send_chat_action(message.chat.id, "upload_document")
    try:
        sections = ai_service.generate_referat(mavzu)
        filepath = docx_service.create_referat_docx(mavzu, sections, message.from_user.id)
    except Exception as e:
        logger.exception("Referat yaratishda xatolik")
        await message.answer(f"❌ Xatolik yuz berdi: {e}")
        return

    await message.answer_document(
        FSInputFile(filepath, filename=f"Referat - {mavzu[:50]}.docx"),
        caption=f'✅ "{mavzu}" mavzusidagi referat tayyor!',
    )
    os.remove(filepath)
    await state.clear()
    await message.answer("Yana nima qilay?", reply_markup=MAIN_MENU)


# ---------------------------------------------------------------------------
# 3) Prezentatsiya tayyorlash bo'limi
# ---------------------------------------------------------------------------
@router.message(F.text == "📊 Prezentatsiya tayyorlash")
async def start_presentation(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_presentation_topic)
    await message.answer(
        "Prezentatsiya mavzusini yozing.\nMasalan: <i>\"O'zbekiston tarixi\"</i>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=CANCEL_TEXT)]], resize_keyboard=True
        ),
    )


@router.message(BotStates.waiting_presentation_topic)
async def handle_presentation_topic(message: Message, state: FSMContext):
    await state.update_data(mavzu=message.text.strip())
    await state.set_state(BotStates.waiting_slide_count)
    await message.answer("Nechta slayd bo'lsin? (masalan: 8). Standart uchun \"8\" deb yozing.")


@router.message(BotStates.waiting_slide_count)
async def handle_slide_count(message: Message, state: FSMContext):
    data = await state.get_data()
    mavzu = data.get("mavzu", "Taqdimot")
    try:
        slide_count = int(message.text.strip())
        slide_count = max(3, min(slide_count, 15))
    except ValueError:
        slide_count = 8

    await message.answer("⏳ Prezentatsiya tayyorlanmoqda, bu biroz vaqt olishi mumkin...")
    await message.bot.send_chat_action(message.chat.id, "upload_document")
    try:
        outline = ai_service.generate_presentation_outline(mavzu, slide_count)
        filepath = pptx_service.create_presentation_pptx(outline, message.from_user.id)
    except Exception as e:
        logger.exception("Prezentatsiya yaratishda xatolik")
        await message.answer(f"❌ Xatolik yuz berdi: {e}")
        return

    await message.answer_document(
        FSInputFile(filepath, filename=f"Prezentatsiya - {mavzu[:50]}.pptx"),
        caption=f'✅ "{mavzu}" mavzusidagi prezentatsiya tayyor!',
    )
    os.remove(filepath)
    await state.clear()
    await message.answer("Yana nima qilay?", reply_markup=MAIN_MENU)


# ---------------------------------------------------------------------------
# Yordamchi funksiyalar
# ---------------------------------------------------------------------------
def _split_text(text: str, max_len: int):
    for i in range(0, len(text), max_len):
        yield text[i : i + max_len]


async def main():
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logger.info("Bot ishga tushdi...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
