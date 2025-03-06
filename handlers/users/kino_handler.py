from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.handler import SkipHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters import Command
from data.config import ADMINS
from handlers.users.middleware import SubscriptionMiddleware
from handlers.users.reklama import ReklamaTuriState
from handlers.users.start import is_subscribed_to_all_channels, get_unsubscribed_channels, get_subscription_keyboard
from loader import dp, bot, kino_db, user_db, channel_db
from keyboards.default.button_kino import menu_movie
from keyboards.default.admin_menu import admin_menu
import asyncio

# Callback - obunani qayta tekshirish

# Middleware ni sozlash
def setup_subscription_middleware():
    dp.middleware.setup(SubscriptionMiddleware())

# Admin paneli
@dp.message_handler(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id in ADMINS:
        await message.answer("Admin paneliga xush kelibsiz! Kerakli bo‘limni tanlang:", reply_markup=admin_menu)
    else:
        await message.answer("Siz admin emassiz.")

# States for kino add and delete
class KinoAdd(StatesGroup):
    kino_add = State()
    kino_code = State()

class KinoDelete(StatesGroup):
    kino_code = State()
    is_confirm = State()

# Statistika ko‘rish
@dp.message_handler(text="📊 Statistika")
async def show_stats(message: types.Message):
    if message.from_user.id in ADMINS:
        try:
            total_kinos = kino_db.count_kinos()
            total_users = user_db.count_users()
            daily_users = user_db.count_daily_users()
            weekly_users = user_db.count_weekly_users()
            monthly_users = user_db.count_monthly_users()

            active_daily = user_db.count_active_daily_users()
            active_weekly = user_db.count_active_weekly_users()
            active_monthly = user_db.count_active_monthly_users()

            stats_message = (
                "📊 <b>Statistika</b>\n\n"
                "🎬 <b>Kinolar</b>\n"
                f" ├ 📂 Jami kinolar: <b>{total_kinos}</b>\n\n"
                "👥 <b>Foydalanuvchilar</b>\n"
                f" ├ 👤 Jami foydalanuvchilar: <b>{total_users}</b>\n"
                f" ├ 🗓 Kunlik yangi: <b>{daily_users}</b>\n"
                f" ├ 📅 Haftalik yangi: <b>{weekly_users}</b>\n"
                f" └ 📆 Oylik yangi: <b>{monthly_users}</b>\n\n"
                "🔥 <b>Faol foydalanuvchilar</b>\n"
                f" ├ 🚀 Kunlik faol: <b>{active_daily}</b>\n"
                f" ├ ⚡️ Haftalik faol: <b>{active_weekly}</b>\n"
                f" └ 🔥 Oylik faol: <b>{active_monthly}</b>"
            )
            await message.answer(stats_message, parse_mode="HTML")
        except Exception as e:
            await message.answer("❌ <b>Statistika olishda xatolik yuz berdi.</b>", parse_mode="HTML")
            print(f"[Xatolik]: {e}")
    else:
        await message.answer("🚫 <b>Siz admin emassiz.</b>", parse_mode="HTML")

# Kino qo‘shish
@dp.message_handler(text="➕ Kino Qo‘shish")
async def message_kino_add(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    if admin_id in ADMINS:
        await KinoAdd.kino_add.set()
        await message.answer("Kinoni yuboring")
    else:
        await message.answer("Siz admin emassiz")

@dp.message_handler(text="🔙 Admin menyu", state=KinoAdd.kino_add)
async def cancel_kino_add(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Jarayon bekor qilindi. Siz bosh menyudasiz.", reply_markup=admin_menu)

@dp.message_handler(state=KinoAdd.kino_add, content_types=types.ContentType.VIDEO)
async def kino_file_handler(message: types.Message, state: FSMContext):
    if message.video is None:
        await message.answer("❌ Video faylni yuborish kerak.")
        return

    async with state.proxy() as data:
        data['file_id'] = message.video.file_id
        data['caption'] = message.caption

    await KinoAdd.kino_code.set()
    await message.answer("📎 <b>Kino uchun Kod kiriting:</b>", parse_mode='HTML')

@dp.message_handler(state=KinoAdd.kino_code, content_types=types.ContentType.TEXT)
async def kino_code_handler(message: types.Message, state: FSMContext):
    try:
        post_id = int(message.text)
        existing_kino = kino_db.search_kino_by_post_id(post_id)
        if existing_kino:
            await message.answer("⚠️ Bu kod bilan kino allaqachon mavjud. Iltimos, boshqa kod kiriting.")
            return

        async with state.proxy() as data:
            data['post_id'] = post_id
            kino_db.add_kino(post_id=data['post_id'], file_id=data['file_id'], caption=data['caption'])

        await message.answer("✅ Kino muvaffaqiyatli qo‘shildi.")
        await state.finish()
    except ValueError:
        await message.answer("❌ Iltimos kino kodni faqat raqam bilan yuboring.")

# Kino o‘chirish
@dp.message_handler(text="🗑 Kino O‘chirish")
async def movie_delete_handler(message: types.Message):
    admin_id = message.from_user.id
    if admin_id in ADMINS:
        await KinoDelete.kino_code.set()
        await message.answer("🗑 O'chirmoqchi bo'lgan kino kodini yuboring")
    else:
        await message.answer("🚫 Siz admin emassiz")

@dp.message_handler(state=KinoDelete.kino_code, content_types=types.ContentType.TEXT)
async def movie_kino_code(message: types.Message, state: FSMContext):
    if message.text == "🔙 Admin menyu":
        await state.finish()
        await message.answer("Jarayon bekor qilindi. Siz bosh menyudasiz.", reply_markup=admin_menu)
        return

    if not message.text.isdigit():
        await message.answer("❌ Iltimos, kino kodini faqat raqam shaklida kiriting.")
        return

    async with state.proxy() as data:
        data['post_id'] = int(message.text)
        result = kino_db.search_kino_by_post_id(data['post_id'])

        if result:
            await message.answer_video(video=result['file_id'], caption=result['caption'])
            await KinoDelete.is_confirm.set()
            await message.answer("Quyidagilardan birini tanlang", reply_markup=menu_movie)
        else:
            await message.answer(f"⚠️ <b>{data['post_id']}</b> kod bilan kino topilmadi.", parse_mode="HTML")

@dp.message_handler(state=KinoDelete.is_confirm, content_types=types.ContentType.TEXT)
async def movie_kino_delete(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['is_confirm'] = message.text
        if data['is_confirm'] == "✅Tasdiqlash":
            kino_db.delete_kino(data['post_id'])
            await message.answer("Kino muvaffaqiyatli o'chirildi", reply_markup=ReplyKeyboardRemove())
            await state.finish()
        elif data['is_confirm'] == "❌Bekor qilish":
            await message.answer("Bekor qilindi", reply_markup=ReplyKeyboardRemove())
            await state.finish()
        else:
            await message.answer("Iltimos quyidagi tugmalardan birini tanlang", reply_markup=menu_movie)

# Kino qidirish (foydalanuvchi tarafi)
@dp.message_handler(lambda x: x.text.isdigit())
async def search_kino_handler(message: types.Message):
    user_id = message.from_user.id
    user_db.update_last_active(user_id)
<<<<<<< HEAD
    if message.text.isdigit():

        post_id = int(message.text)
        data = kino_db.search_kino_by_post_id(post_id)
        if data:
            try:
                # Send the video to the user
                await bot.send_video(
                    chat_id=message.from_user.id,
                    video=data['file_id'],
                    caption=f"{data['caption']} \n\n🗂Kinoni Yuklash Soni: {data['count_download']} \n\n📌 Barcha kinolar:  T.me/Kino_Mania_2024"
                )

                # Update the download count in the database
                kino_db.update_download_count(post_id)
            except Exception as err:
                await message.answer(f"Kino topildi lekin yuborishda xatolik: {err}")
        else:
            await message.answer(f"{post_id} kod bilan kino topilmadi")
=======
    post_id = int(message.text)
    data = kino_db.search_kino_by_post_id(post_id)
    if data:
        try:
            await bot.send_video(
                chat_id=user_id,
                video=data['file_id'],
                caption=(
                    f"<b>{data['caption']}</b>\n\n"
                    f"📥 <b>Kino Yuklash Soni:</b> {data['count_download']}\n\n"
                    f"📌 <b>Barcha kinolar:</b> T.me/Kino_Mania_2024\n\n"
                ),
                parse_mode='HTML'
            )
            kino_db.update_download_count(post_id)
        except Exception as err:
            await message.answer(f"❌ Kino yuborishda xatolik: {err}", parse_mode='HTML')
>>>>>>> 99f03178aa892f756ba97f7af927ce9c921321a0
    else:
        await message.answer(f"⚠️ <b>{post_id}</b> kodi bilan kino topilmadi.", parse_mode="HTML")

# Bosh menyuga qaytish
@dp.message_handler(text="🔙 Admin menyu", state=[ReklamaTuriState.tur, KinoDelete.kino_code, KinoAdd.kino_code])
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Jarayon Bekor Bo'ldi Admin Menyudasiz.", reply_markup=admin_menu)

# Bekor qilish handleri
@dp.message_handler(
    lambda message: message.text in ["➕ Kino Qo‘shish", "📊 Statistika", "📣 Reklama", "🗑 Kino O‘chirish"], state="*")
@dp.message_handler(lambda message: message.text.lower() in ["bekor qilish", "/cancel"], state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.finish()
    if message.from_user.id in ADMINS:
        await message.answer("Jarayon bekor qilindi. Siz Admin menyudasiz.", reply_markup=admin_menu)
    else:
        await message.answer("Jarayon bekor qilindi.", reply_markup=ReplyKeyboardRemove())

# Middleware ni faollashtirish
setup_subscription_middleware()