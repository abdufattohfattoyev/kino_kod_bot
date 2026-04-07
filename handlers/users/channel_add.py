from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from data.config import ADMINS
from keyboards.default.admin_menu import admin_menu
from loader import dp, channel_db, bot

# Inline klaviaturalar
def get_channel_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ Kanal Qo‘shish", callback_data="add_channel"),
        InlineKeyboardButton("📜 Kanallar Ro‘yxati", callback_data="list_channels"),
        InlineKeyboardButton("🗑 Kanal O‘chirish", callback_data="delete_channel")
    )
    return markup

def get_confirm_keyboard(channel_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"confirm_add_{channel_id}"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")
    )
    return markup

def get_delete_keyboard(channels):
    markup = InlineKeyboardMarkup(row_width=1)
    for channel_id, title, static_link in channels:
        markup.add(InlineKeyboardButton(f"{title} ({channel_id})", callback_data=f"delete_{channel_id}"))
    markup.add(InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu"))
    return markup

# Kanal qo‘shish uchun holat
class ChannelAdd(StatesGroup):
    channel_link = State()

# Kanal bo’limi
@dp.message_handler(text="📢 Kanallar")
async def channel_section(message: types.Message):
    if message.from_user.id in ADMINS:
        await message.answer("Kanallar Bo'limi", reply_markup=get_channel_menu())
    else:
        await message.answer("🚫 Siz admin emassiz.")

# Kanal qo‘shish boshlanishi
@dp.callback_query_handler(lambda c: c.data == "add_channel")
async def start_add_channel(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id in ADMINS:
        await ChannelAdd.channel_link.set()
        await callback.message.edit_text(
            "📌 Kanal linkini yuboring (masalan, @ChannelName).\n"
            "Shaxsiy kanallar uchun botni oldindan admin qilib qo‘shing va kanal ID sini yuboring (masalan, -100123456789)."
        )
        await callback.answer()
    else:
        await callback.answer("🚫 Siz admin emassiz.", show_alert=True)

# Kanal linkini qayta ishlash
@dp.message_handler(state=ChannelAdd.channel_link, content_types=types.ContentType.TEXT)
async def process_channel_link(message: types.Message, state: FSMContext):
    channel_input = message.text.strip()
    try:
        if channel_input.startswith('-100'):
            channel_id = int(channel_input)
            channel = await bot.get_chat(channel_id)
        elif channel_input.startswith('@'):
            channel = await bot.get_chat(channel_input)
            channel_id = channel.id
        else:
            await message.answer("❌ Noto‘g‘ri format. @ChannelName yoki kanal ID sini yuboring.")
            return

        channel_title = channel.title

        # Kanal havolasini faqat bir marta yaratish va statik qilib saqlash
        if channel_db.channel_exists(channel_id):
            static_link = channel_db.get_channel_link(channel_id)
        else:
            try:
                static_link = await bot.export_chat_invite_link(channel_id)
            except Exception:
                static_link = f"Shaxsiy kanal ID: {channel_id}"

        if channel_db.channel_exists(channel_id):
            await message.answer("⚠️ Bu kanal allaqachon mavjud.")
            await state.finish()
            return

        await message.answer(
            f"📢 Kanal: <b>{channel_title}</b>\nID: <b>{channel_id}</b>\nHavola: <b>{static_link}</b>\nTasdiqlaysizmi?",
            parse_mode="HTML",
            reply_markup=get_confirm_keyboard(channel_id)
        )
        async with state.proxy() as data:
            data['channel_id'] = channel_id
            data['channel_title'] = channel_title
            data['static_link'] = static_link
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}. Botni kanalga admin qilib qo‘shing.")
        await state.finish()

# Tasdiqlash
@dp.callback_query_handler(lambda c: c.data.startswith("confirm_add_"), state=ChannelAdd.channel_link)
async def confirm_channel_add(callback: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split("_")[2])
    async with state.proxy() as data:
        channel_db.add_channel(data['channel_id'], data['channel_title'], data['static_link'])
    await callback.message.edit_text("✅ Kanal qo‘shildi!", reply_markup=get_channel_menu())
    await state.finish()

# Bekor qilish
@dp.callback_query_handler(lambda c: c.data == "cancel_add", state="*")
async def cancel_channel_add(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Kanal qo‘shish bekor qilindi.", reply_markup=get_channel_menu())
    await state.finish()

# Kanallar ro‘yxati
@dp.callback_query_handler(lambda c: c.data == "list_channels")
async def list_channels(callback: types.CallbackQuery):
    if callback.from_user.id in ADMINS:
        channels = channel_db.get_all_channels()
        if channels:
            response = "📜 <b>Kanallar ro‘yxati:</b>\n\n"
            for i, (channel_id, title, static_link) in enumerate(channels, 1):
                response += f"{i}. {title} (<code>{channel_id}</code>)\n   Havola: {static_link}\n"
        else:
            response = "📭 Hozircha kanallar yo‘q."
        await callback.message.edit_text(response, parse_mode="HTML", reply_markup=get_channel_menu())
        await callback.answer()
    else:
        await callback.answer("🚫 Siz admin emassiz.", show_alert=True)

# Kanal o‘chirish
@dp.callback_query_handler(lambda c: c.data == "delete_channel")
async def start_delete_channel(callback: types.CallbackQuery):
    if callback.from_user.id in ADMINS:
        channels = channel_db.get_all_channels()
        if channels:
            await callback.message.edit_text("🗑 O‘chirmoqchi bo‘lgan kanalni tanlang:",
                                             reply_markup=get_delete_keyboard(channels))
        else:
            await callback.message.edit_text("📭 O‘chirish uchun kanal yo‘q.", reply_markup=get_channel_menu())
        await callback.answer()
    else:
        await callback.answer("🚫 Siz admin emassiz.", show_alert=True)

@dp.callback_query_handler(lambda c: c.data.startswith("delete_"))
async def confirm_delete_channel(callback: types.CallbackQuery):
    channel_id = int(callback.data.split("_")[1])
    channel_db.delete_channel(channel_id)
    await callback.message.edit_text(f"✅ Kanal (<code>{channel_id}</code>) o‘chirildi.", parse_mode="HTML",
                                     reply_markup=get_channel_menu())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def back_to_channel_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("Kanal bo‘limi:", reply_markup=get_channel_menu())
    await callback.answer()

# Bekor qilish uchun handler
@dp.message_handler(text="🔙 Admin menyu", state="*")
async def back_to_admin_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Siz admin menyudasiz.", reply_markup=admin_menu)

# Kanal ID sini olish
@dp.message_handler(commands=["get_channel_id"])
async def get_channel_id(message: types.Message):
    if message.chat.type in ["group", "supergroup", "channel"]:
        channel_id = message.chat.id
        channel_title = message.chat.title
        await message.answer(f"Kanal ID: <code>{channel_id}</code>\nNomi: {channel_title}", parse_mode="HTML")
    else:
        await message.answer("Bu buyruqni guruh yoki kanal ichida ishlatish kerak!")