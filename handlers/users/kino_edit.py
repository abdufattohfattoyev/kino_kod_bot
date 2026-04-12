import logging

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from data.config import ADMINS
from keyboards.default.admin_menu import admin_menu
from loader import dp, kino_db, user_db

logger = logging.getLogger(__name__)


class KinoEditState(StatesGroup):
    enter_code  = State()   # Kod so'rash
    choose_what = State()   # Nima o'zgartirish: caption yoki fayl
    enter_value = State()   # Yangi qiymat kiritish


def _is_admin(user_id: int) -> bool:
    return user_id in ADMINS or user_db.check_if_admin(user_id)


def _choose_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("✏️ Sarlavhani o'zgartirish", callback_data="edit_caption"),
        InlineKeyboardButton("🎬 Faylni o'zgartirish",     callback_data="edit_file"),
        InlineKeyboardButton("❌ Bekor qilish",             callback_data="edit_cancel"),
    )


@dp.message_handler(text="✏️ Kino Tahrirlash")
async def kino_edit_start(message: types.Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await message.answer("🚫 Siz admin emassiz.")
        return
    await KinoEditState.enter_code.set()
    await message.answer(
        "✏️ <b>Kino Tahrirlash</b>\n\n"
        "Tahrirlash uchun kino kodini yuboring:",
        parse_mode="HTML"
    )


@dp.message_handler(state=KinoEditState.enter_code, content_types=types.ContentType.TEXT)
async def kino_edit_code(message: types.Message, state: FSMContext):
    if message.text.strip() == "🔙 Admin menyu":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu)
        return

    if not message.text.strip().isdigit():
        await message.answer("❌ Faqat raqam (kino kodi) kiriting.")
        return

    post_id = int(message.text.strip())
    kino = kino_db.search_kino_by_post_id(post_id)
    if not kino:
        await message.answer(f"⚠️ <b>{post_id}</b> kodi bilan kino topilmadi.", parse_mode="HTML")
        return

    parts_count = kino_db.count_parts(post_id)
    async with state.proxy() as data:
        data["post_id"] = post_id
        data["caption"] = kino["caption"]

    await KinoEditState.choose_what.set()
    await message.answer(
        f"🎬 <b>{kino['caption']}</b>\n"
        f"📦 Qismlar: <b>{parts_count} ta</b>\n"
        f"📥 Yuklashlar: <b>{kino['count_download']}</b>\n\n"
        "Nima o'zgartirmoqchisiz?",
        parse_mode="HTML",
        reply_markup=_choose_markup()
    )


@dp.callback_query_handler(lambda c: c.data in ("edit_caption", "edit_file", "edit_cancel"),
                            state=KinoEditState.choose_what)
async def kino_edit_choose(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "edit_cancel":
        await state.finish()
        await callback.message.edit_text("❌ Bekor qilindi.")
        await callback.message.answer("Admin menyu:", reply_markup=admin_menu)
        await callback.answer()
        return

    async with state.proxy() as data:
        data["edit_type"] = callback.data

    if callback.data == "edit_caption":
        await callback.message.edit_text(
            "✏️ <b>Yangi sarlavhani yuboring:</b>",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "🎬 <b>Yangi videoni yuboring:</b>\n"
            "(Bu faqat asosiy (1-qism) faylni almashtiradi)",
            parse_mode="HTML"
        )

    await KinoEditState.enter_value.set()
    await callback.answer()


@dp.message_handler(state=KinoEditState.enter_value, content_types=types.ContentType.TEXT)
async def kino_edit_caption(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if data.get("edit_type") != "edit_caption":
            await message.answer("🎬 Iltimos, video yuboring.")
            return
        post_id = data["post_id"]

    new_caption = message.text.strip()
    kino_db.update_caption(post_id, new_caption)
    await state.finish()
    await message.answer(
        f"✅ <b>Sarlavha yangilandi!</b>\n"
        f"🔑 Kod: <code>{post_id}</code>\n"
        f"📝 Yangi sarlavha: <b>{new_caption}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu
    )


@dp.message_handler(state=KinoEditState.enter_value, content_types=types.ContentType.VIDEO)
async def kino_edit_file(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if data.get("edit_type") != "edit_file":
            await message.answer("✏️ Iltimos, matn yuboring.")
            return
        post_id = data["post_id"]
        caption = data["caption"]

    new_file_id = message.video.file_id
    kino_db.update_file_id(post_id, new_file_id)

    # KinoParts dagi 1-qismni ham yangilaymiz
    try:
        from loader import kino_db as kdb
        kdb.execute(
            "UPDATE KinoParts SET file_id = ? WHERE post_id = ? AND part_number = 1",
            parameters=(new_file_id, post_id), commit=True
        )
    except Exception as e:
        logger.warning(f"KinoParts 1-qismni yangilashda xatolik: {e}")

    await state.finish()
    await message.answer(
        f"✅ <b>Kino fayli yangilandi!</b>\n"
        f"🔑 Kod: <code>{post_id}</code>\n"
        f"🎬 <b>{caption}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu
    )
