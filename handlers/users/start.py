from aiogram import types
from aiogram.dispatcher.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from data.config import ADMINS
from keyboards.default.kanal_button import kanal_keyboard
from loader import dp, bot, user_db, channel_db
import asyncio

# Obuna tekshirish funksiyasi
async def check_subscription(user_id: int, channel_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"❌ Xatolik: {channel_id} kanalida foydalanuvchi {user_id} ni tekshirishda: {e}")
        return False

# Foydalanuvchi barcha kanallarga obuna bo'lganligini tekshirish
async def is_subscribed_to_all_channels(user_id: int) -> bool:
    channels = channel_db.get_all_channels()
    if not channels:
        return True
    for channel_id, _, _ in channels:
        if not await check_subscription(user_id, channel_id):
            return False
    return True

# Obuna bo'lmagan kanallar ro'yxatini olish (statik havola bilan)
async def get_unsubscribed_channels(user_id: int) -> list:
    channels = channel_db.get_all_channels()
    unsubscribed = []
    for channel_id, title, static_link in channels:
        if not await check_subscription(user_id, channel_id):
            unsubscribed.append((static_link, title))  # Statik havola ishlatiladi
    return unsubscribed

# Inline klaviatura yaratish



def get_subscription_keyboard(unsubscribed_channels):
    markup = InlineKeyboardMarkup(row_width=1)

    for index, (invite_link, _) in enumerate(unsubscribed_channels, start=1):
        if invite_link.startswith("https://t.me/"):  # Ommaviy yoki shaxsiy kanal uchun URL
            markup.add(InlineKeyboardButton(f"{index}. ➕ Obuna bo‘lish", url=invite_link))
        else:
            markup.add(InlineKeyboardButton(f"{index}. ➕ Obuna bo‘lish (Shaxsiy kanal)", callback_data="no_action"))

    markup.add(InlineKeyboardButton("✅ Azo bo'ldim", callback_data="check_subscription"))
    return markup


def get_remaining_channels_message(remaining_count):
    if remaining_count == 0:
        return "🎉 Barcha kanallarga obuna bo‘ldingiz!"
    else:
        return f"📌 Hali {remaining_count} ta kanalga obuna bo‘lishingiz kerak!"


# Avtomatik tekshirish va yangilash funksiyasi
async def auto_check_subscription(user_id: int, message: types.Message):
    while True:
        await asyncio.sleep(5)  # Har 5 soniyada tekshirish
        if await is_subscribed_to_all_channels(user_id):
            new_text = "👋 <b>Assalomu alaykum,Kino Botga xush kelibsiz.</b>\n\n✍🏻<b>Kino kodini yuboring.</b>"
            if message.text != new_text:
                await message.edit_text(new_text, parse_mode="HTML")
            break
        else:
            unsubscribed = await get_unsubscribed_channels(user_id)
            new_text = "⚠️ <b>Siz hali barcha kanallarga obuna bo'lmadingiz!</b>\n\n👇 Quyidagilarga obuna bo'ling:"
            new_reply_markup = get_subscription_keyboard(unsubscribed)
            if message.text != new_text or message.reply_markup != new_reply_markup:
                await message.edit_text(new_text, reply_markup=new_reply_markup, parse_mode="HTML")

# Callback - obunani tekshirish
@dp.callback_query_handler(lambda c: c.data == "check_subscription")
async def check_subscription_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if isinstance(ADMINS, list) and user_id in ADMINS:
        new_text = "👑 <b>Siz adminsiz, obuna shart emas.</b>"
        if callback.message.text != new_text:
            await callback.message.edit_text(new_text, parse_mode="HTML")
        await callback.answer()
        return

    if await is_subscribed_to_all_channels(user_id):
        new_text = "👋 <b>Assalomu alaykum,Kino Botga xush kelibsiz.</b>\n\n✍🏻<b>Kino kodini yuboring.</b>"
        if callback.message.text != new_text:
            await callback.message.edit_text(new_text, parse_mode="HTML")
        await callback.answer()
        return
    else:
        unsubscribed = await get_unsubscribed_channels(user_id)
        new_text = "⚠️ <b>Siz hali barcha kanallarga obuna bo'lmadingiz!</b>\n\n👇 Quyidagilarga obuna bo'ling:"
        new_reply_markup = get_subscription_keyboard(unsubscribed)
        if callback.message.reply_markup != new_reply_markup or callback.message.text != new_text:
            await callback.message.edit_text(new_text, reply_markup=new_reply_markup, parse_mode="HTML")
        await callback.answer()

# /start komandasi
@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or f"User ID: {message.from_user.full_name}"

    # Foydalanuvchi mavjudligini tekshirish
    if not user_db.select_user(user_id):
        # Foydalanuvchini ro‘yxatga olish
        user_db.add_user(user_id, username)

        # Foydalanuvchilar sonini olish
        user_count = user_db.count_users()

    if message.chat.type == "private":
        if not user_db.select_user(user_id):
            user_db.add_user(user_id, username)
            user_count = user_db.count_users()
            for admin in ADMINS:
                try:
                    await dp.bot.send_message(
                        admin,
                        f"🆕 Yangi foydalanuvchi: @{username}\n👥 Jami foydalanuvchilar soni: {user_count}"
                    )
                except Exception as e:
                    print(f"Admin {admin} ga xabar yuborishda xato: {e}")

        user_db.update_last_active(user_id)


        if channel_db.get_all_channels():
            if not await is_subscribed_to_all_channels(user_id):
                unsubscribed = await get_unsubscribed_channels(user_id)
                text = "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:</b>"
                markup = get_subscription_keyboard(unsubscribed)
                msg = await message.answer(text, reply_markup=markup, parse_mode="HTML")
                asyncio.create_task(auto_check_subscription(user_id, msg))
            else:
                await message.answer(
                    f"👋 Assalomu alaykum, {message.from_user.full_name}! Kino Botga xush kelibsiz.\n\n✍🏻 Kino kodini yuboring.",
                    reply_markup=kanal_keyboard
                )
        else:
            await message.answer(
                f"👋 Assalomu alaykum, {message.from_user.full_name}! Kino Botga xush kelibsiz.\n\n✍🏻 Kino kodini yuboring.",
                reply_markup=kanal_keyboard
            )
    else:
        await message.reply("👋 Botdan shaxsiy chatda foydalanishingiz mumkin!")

# "📽 Barcha kinolar" tugmasi
@dp.message_handler(lambda message: message.text == "📽 Barcha kinolar")
async def send_channel_link(message: types.Message):
    await message.answer(
        "<b>🎬 Yangi kinolarni birinchi bo'lib ko'rish uchun kanalimizga a'zo bo'ling:</b>\n\n"
        "<b>📌 Kanal:</b>  https://t.me/Kino_mania_2024",
        parse_mode="HTML"
    )

# Shaxsiy kanal uchun no_action callback
@dp.callback_query_handler(lambda c: c.data == "no_action")
async def no_action_callback(callback: types.CallbackQuery):
    await callback.answer("Bu shaxsiy kanal. Iltimos, kanal adminidan tasdiq so‘rang.", show_alert=True)
