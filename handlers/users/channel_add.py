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

# Kanal qo’shish uchun holat
class ChannelAdd(StatesGroup):
    channel_id = State()    # 1-qadam: kanal ID yoki @username
    channel_link = State()  # 2-qadam: taklif havola


# Kanal bo’limi
@dp.message_handler(text="📢 Kanallar")
async def channel_section(message: types.Message):
    if message.from_user.id in ADMINS:
        await message.answer("Kanallar Bo’limi", reply_markup=get_channel_menu())
    else:
        await message.answer("🚫 Siz admin emassiz.")


# Kanal qo’shish boshlanishi
@dp.callback_query_handler(lambda c: c.data == "add_channel")
async def start_add_channel(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMINS:
        await callback.answer("🚫 Siz admin emassiz.", show_alert=True)
        return
    await ChannelAdd.channel_id.set()
    await callback.message.edit_text(
        "📌 <b>1-qadam:</b> Quyidagilardan birini yuboring:\n\n"
        "• <code>@ChannelUsername</code>\n"
        "• <code>-100123456789</code>\n"
        "• <code>https://t.me/+xxxxxxxx</code> (shaxsiy kanal)\n\n"
        "<i>Bot kanalda admin bo’lishi tavsiya etiladi!</i>",
        parse_mode="HTML"
    )
    await callback.answer()


def _is_invite_link(text: str) -> bool:
    return text.startswith("https://t.me/+") or text.startswith("https://t.me/joinchat/")


# 1-qadam: kanal ID/username/havola ni qayta ishlash
@dp.message_handler(state=ChannelAdd.channel_id, content_types=types.ContentType.TEXT)
async def process_channel_id(message: types.Message, state: FSMContext):
    if message.text.strip() == "🔙 Admin menyu":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu)
        return

    channel_input = message.text.strip()

    # Foydalanuvchi invite link yuborgan holat
    if _is_invite_link(channel_input):
        async with state.proxy() as data:
            data["static_link"] = channel_input
            data["waiting_for"] = "id"
        await message.answer(
            "🔗 Havola saqlandi.\n\n"
            "📌 Endi kanal ID sini yuboring:\n"
            "<code>-100123456789</code>",
            parse_mode="HTML"
        )
        await ChannelAdd.channel_link.set()
        return

    # ID yoki @username
    try:
        if channel_input.startswith("-100") and channel_input[1:].isdigit():
            channel_id = int(channel_input)
            channel = await bot.get_chat(channel_id)
        elif channel_input.startswith("@"):
            channel = await bot.get_chat(channel_input)
            channel_id = channel.id
        else:
            await message.answer(
                "❌ Noto’g’ri format. Quyidagilardan birini yuboring:\n"
                "• <code>@ChannelUsername</code>\n"
                "• <code>-100123456789</code>\n"
                "• <code>https://t.me/+xxxxxxxx</code>",
                parse_mode="HTML"
            )
            return
    except Exception as e:
        await message.answer(
            f"❌ Kanal topilmadi: <code>{e}</code>\n"
            "Bot kanalda admin ekanligini tekshiring.",
            parse_mode="HTML"
        )
        return

    if channel_db.channel_exists(channel_id):
        await message.answer("⚠️ Bu kanal allaqachon qo’shilgan.")
        await state.finish()
        return

    # Avtomatik havola olishga urinamiz
    auto_link = None
    try:
        auto_link = await bot.export_chat_invite_link(channel_id)
    except Exception:
        pass

    async with state.proxy() as data:
        data["channel_id"] = channel_id
        data["channel_title"] = channel.title

    if auto_link:
        async with state.proxy() as data:
            data["static_link"] = auto_link
            data["waiting_for"] = "confirm"
        await message.answer(
            f"📢 <b>Kanal:</b> {channel.title}\n"
            f"🆔 <b>ID:</b> <code>{channel_id}</code>\n"
            f"🔗 <b>Havola:</b> {auto_link}\n\n"
            "Tasdiqlaysizmi?",
            parse_mode="HTML",
            reply_markup=get_confirm_keyboard(channel_id)
        )
    else:
        async with state.proxy() as data:
            data["waiting_for"] = "link"
        await message.answer(
            f"📢 <b>Kanal:</b> {channel.title}\n"
            f"🆔 <b>ID:</b> <code>{channel_id}</code>\n\n"
            "📌 Kanal taklif havolasini yuboring:\n"
            "<i>https://t.me/+xxxxxxxx</i>",
            parse_mode="HTML"
        )
    await ChannelAdd.channel_link.set()


# 2-qadam: link yoki ID kutish
@dp.message_handler(state=ChannelAdd.channel_link, content_types=types.ContentType.TEXT)
async def process_channel_link(message: types.Message, state: FSMContext):
    if message.text.strip() == "🔙 Admin menyu":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu)
        return

    async with state.proxy() as data:
        waiting_for = data.get("waiting_for", "link")

    # Tasdiqlash tugmasi kutilmoqda - matn kerak emas
    if waiting_for == "confirm":
        await message.answer("Iltimos, quyidagi tugmalardan foydalaning.")
        return

    # Invite link yuborilgandan keyin kanal ID kutilmoqda
    if waiting_for == "id":
        inp = message.text.strip()
        if not (inp.startswith("-100") and inp[1:].isdigit()):
            await message.answer(
                "❌ Faqat kanal ID yuboring:\n<code>-100123456789</code>",
                parse_mode="HTML"
            )
            return
        try:
            channel_id = int(inp)
            channel = await bot.get_chat(channel_id)
        except Exception as e:
            await message.answer(f"❌ Kanal topilmadi: <code>{e}</code>", parse_mode="HTML")
            return

        if channel_db.channel_exists(channel_id):
            await message.answer("⚠️ Bu kanal allaqachon qo’shilgan.")
            await state.finish()
            return

        async with state.proxy() as data:
            data["channel_id"] = channel_id
            data["channel_title"] = channel.title
            data["waiting_for"] = "confirm"
            link = data["static_link"]

        await message.answer(
            f"📢 <b>Kanal:</b> {channel.title}\n"
            f"🆔 <b>ID:</b> <code>{channel_id}</code>\n"
            f"🔗 <b>Havola:</b> {link}\n\n"
            "Tasdiqlaysizmi?",
            parse_mode="HTML",
            reply_markup=get_confirm_keyboard(channel_id)
        )
        return

    # Kanal ID yuborilgandan keyin link kutilmoqda
    link_input = message.text.strip()
    if not _is_invite_link(link_input):
        await message.answer(
            "❌ Noto’g’ri havola.\n"
            "<i>Misol: https://t.me/+xxxxxxxx</i>",
            parse_mode="HTML"
        )
        return

    async with state.proxy() as data:
        data["static_link"] = link_input
        data["waiting_for"] = "confirm"
        title = data["channel_title"]
        cid = data["channel_id"]

    await message.answer(
        f"📢 <b>Kanal:</b> {title}\n"
        f"🆔 <b>ID:</b> <code>{cid}</code>\n"
        f"🔗 <b>Havola:</b> {link_input}\n\n"
        "Tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard(cid)
    )

# Tasdiqlash
@dp.callback_query_handler(lambda c: c.data.startswith("confirm_add_"), state=ChannelAdd.channel_link)
async def confirm_channel_add(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        channel_db.add_channel(data["channel_id"], data["channel_title"], data["static_link"])
    await callback.message.edit_text("✅ Kanal qo’shildi!", reply_markup=get_channel_menu())
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