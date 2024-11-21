from aiogram import types
from aiogram.dispatcher.filters import CommandStart
from loader import dp, user_db
from data.config import ADMINS

@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Ismi yo'q"

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

    # Foydalanuvchi mavjud bo‘lsa ham, uning faoliyatini yangilash
    user_db.update_last_active(user_id)

    # Foydalanuvchiga xush kelibsiz xabari
    await message.answer(
        f"👋 Assalomu alaykum, {message.from_user.full_name}!Kino Botga xush kelibsiz.\n\n✍🏻 Kino kodini yuboring."
    )
