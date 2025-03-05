from aiogram import types
from aiogram.dispatcher.filters import CommandStart
from loader import dp, user_db
from data.config import ADMINS
from keyboards.default.kanal_button import kanal_keyboard

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

        # Adminlarga yangi foydalanuvchi haqida xabar yuborish
        for admin in ADMINS:
            try:
                await dp.bot.send_message(
                    admin,
                    f"🆕 Yangi foydalanuvchi: @{username}\n👥 Jami foydalanuvchilar soni: {user_count}"
                )
            except Exception as e:
                print(f"Admin {admin} ga xabar yuborishda xato: {e}")

    user_db.update_last_active(user_id)

    await message.answer(
        f"👋 Assalomu alaykum, {message.from_user.full_name}! Kino Botga xush kelibsiz.\n\n✍🏻 Kino kodini yuboring.",
        reply_markup=kanal_keyboard  # Alohida fayldan tugmani qo‘shamiz
    )

@dp.message_handler(lambda message: message.text == "📽 Barcha kinolar")
async def send_channel_link(message: types.Message):
    await message.answer("🎬 Yangi kinolarni birinchi bo'lib ko'rish uchun kanalimizga a'zo bo'ling:\n\n"
                         "https://t.me/KINO_MANIA_2024")

