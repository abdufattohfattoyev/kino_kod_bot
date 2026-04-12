import logging

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from data.config import ADMINS
from keyboards.default.admin_menu import admin_menu
from loader import dp, bot, user_db

logger = logging.getLogger(__name__)


class BlockUserState(StatesGroup):
    enter_id = State()


class UnblockUserState(StatesGroup):
    enter_id = State()


def _is_admin(user_id: int) -> bool:
    return user_id in ADMINS or user_db.check_if_admin(user_id)


# ── Bloklash ──────────────────────────────────────────────────────────────────

@dp.message_handler(text="🚫 Bloklash")
async def block_user_start(message: types.Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await message.answer("🚫 Siz admin emassiz.")
        return
    await BlockUserState.enter_id.set()
    await message.answer(
        "🚫 <b>Bloklash</b>\n\n"
        "Bloklash uchun foydalanuvchining Telegram ID sini kiriting\n"
        "yoki <b>username</b>ini @username ko'rinishida yuboring:\n\n"
        "Bekor qilish: <code>🔙 Admin menyu</code>",
        parse_mode="HTML"
    )


@dp.message_handler(state=BlockUserState.enter_id, content_types=types.ContentType.TEXT)
async def block_user_id(message: types.Message, state: FSMContext):
    if message.text.strip() == "🔙 Admin menyu":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu)
        return

    text = message.text.strip()
    user = None

    try:
        telegram_id = int(text)
        user = user_db.select_user(telegram_id)
    except ValueError:
        # username bo'lishi mumkin
        await message.answer("❌ Faqat raqam (Telegram ID) kiriting.")
        return

    if not user:
        await message.answer("❌ Bu ID bilan foydalanuvchi topilmadi.\nFoydalanuvchi avval bot bilan suhbat boshlagan bo'lishi kerak.")
        return

    if telegram_id in ADMINS or user_db.check_if_admin(telegram_id):
        await message.answer("⚠️ Adminni bloklash mumkin emas.")
        return

    if user_db.is_user_blocked(telegram_id):
        await message.answer(f"⚠️ Foydalanuvchi (ID: <code>{telegram_id}</code>) allaqachon bloklangan.", parse_mode="HTML")
        await state.finish()
        return

    user_db.block_user(telegram_id)
    username = user[2] or "—"
    await message.answer(
        f"✅ Foydalanuvchi bloklandi!\n"
        f"👤 ID: <code>{telegram_id}</code>\n"
        f"🔗 Username: @{username}",
        parse_mode="HTML",
        reply_markup=admin_menu
    )
    try:
        await bot.send_message(telegram_id, "🚫 <b>Siz botdan bloklangansiz.</b>", parse_mode="HTML")
    except Exception:
        pass
    await state.finish()


# ── Blokdan chiqarish ─────────────────────────────────────────────────────────

@dp.message_handler(text="✅ Blokdan Chiqarish")
async def unblock_user_start(message: types.Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await message.answer("🚫 Siz admin emassiz.")
        return

    blocked = user_db.get_blocked_users()
    if not blocked:
        await message.answer("📭 Hozirda bloklangan foydalanuvchi yo'q.")
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for tid, uname in blocked:
        label = f"👤 {uname or tid}  (ID: {tid})"
        markup.add(InlineKeyboardButton(label, callback_data=f"unblock_{tid}"))

    await message.answer(
        f"🔓 <b>Bloklangan foydalanuvchilar ({len(blocked)} ta)</b>\n"
        "Blokdan chiqarish uchun tanlang:",
        parse_mode="HTML",
        reply_markup=markup
    )


@dp.callback_query_handler(lambda c: c.data.startswith("unblock_"))
async def unblock_user_cb(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫 Siz admin emassiz.", show_alert=True)
        return

    telegram_id = int(callback.data.split("_", 1)[1])
    user_db.unblock_user(telegram_id)
    await callback.message.edit_text(
        f"✅ Foydalanuvchi (ID: <code>{telegram_id}</code>) blokdan chiqarildi.",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(telegram_id, "✅ <b>Sizning blokingiz olib tashlandi. Botdan foydalanishingiz mumkin.</b>", parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


# ── Bloklangan ro'yxat ────────────────────────────────────────────────────────

@dp.message_handler(text="📋 Bloklangan Ro'yxat")
async def blocked_list(message: types.Message):
    if not _is_admin(message.from_user.id):
        await message.answer("🚫 Siz admin emassiz.")
        return

    blocked = user_db.get_blocked_users()
    if not blocked:
        await message.answer("📭 Hozirda bloklangan foydalanuvchi yo'q.")
        return

    lines = [f"🚫 <b>Bloklangan foydalanuvchilar ({len(blocked)} ta):</b>\n"]
    for tid, uname in blocked:
        lines.append(f"👤 <code>{tid}</code>  @{uname or '—'}")

    await message.answer("\n".join(lines), parse_mode="HTML")
