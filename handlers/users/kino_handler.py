from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove
from data.config import ADMINS
from loader import dp, bot, kino_db, user_db
from keyboards.default.button_kino import menu_movie
import asyncio

# States for kino add and delete
class KinoAdd(StatesGroup):
    kino_add = State()
    kino_code = State()

class KinoDelete(StatesGroup):
    kino_code = State()
    is_confirm = State()

# Command to view stats (for admins)
@dp.message_handler(commands="stats")
async def show_stats(message: types.Message):
    if message.from_user.id in ADMINS:
        total_kinos = kino_db.count_kinos()
        total_users = user_db.count_users()
        daily_users = user_db.count_daily_users()
        weekly_users = user_db.count_weekly_users()
        monthly_users = user_db.count_monthly_users()

        active_daily = user_db.count_active_daily_users()
        active_weekly = user_db.count_active_weekly_users()
        active_monthly = user_db.count_active_monthly_users()

        stats_message = (
            f"📊 Statistika:\n"
            f"- Kinolar soni: {total_kinos}\n"
            f"- Jami foydalanuvchilar: {total_users}\n"
            f"- Kunlik yangi foydalanuvchilar: {daily_users}\n"
            f"- Haftalik yangi foydalanuvchilar: {weekly_users}\n"
            f"- Oylik yangi foydalanuvchilar: {monthly_users}\n\n"
            f"Faol foydalanuvchilar:\n"
            f"- Kunlik faol: {active_daily}\n"
            f"- Haftalik faol: {active_weekly}\n"
            f"- Oylik faol: {active_monthly}"
        )
        await message.answer(stats_message)
    else:
        await message.answer("Siz admin emassiz.")



# Command to count total users in the database (for admins)
@dp.message_handler(commands="count_users")
async def message_count_users(message: types.Message):
    admin_id = message.from_user.id
    if admin_id in ADMINS:
        user_count = user_db.count_users()
        await message.answer(f"Bazada {user_count} ta foydalanuvchi bor")
    else:
        await message.answer("Siz admin emassiz")


# Command to show new kinolar (for admins)
@dp.message_handler(commands="new_kinos")
async def show_new_kinos(message: types.Message):
    new_kinos = kino_db.get_new_kinos()
    if new_kinos:
        for file_id, caption in new_kinos:
            await message.answer_video(video=file_id, caption=caption)
    else:
        await message.answer("Yangi kinolar mavjud emas.")

# Handler for adding a new kino (for admins)
@dp.message_handler(commands="kino_add")
async def message_kino_add(message: types.Message):
    admin_id = message.from_user.id
    if admin_id in ADMINS:
        await KinoAdd.kino_add.set()
        await message.answer("Kinoni yuboring")
    else:
        await message.answer("Siz admin emassiz")

# Handler for kino file upload
@dp.message_handler(state=KinoAdd.kino_add, content_types=types.ContentType.VIDEO)
async def kino_file_handler(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['file_id'] = message.video.file_id
        data['caption'] = message.caption
    await KinoAdd.kino_code.set()
    await message.answer("Kino uchun Kod kiriting")

# Handler for kino code input
@dp.message_handler(state=KinoAdd.kino_code, content_types=types.ContentType.TEXT)
async def kino_code_handler(message: types.Message, state: FSMContext):
    try:
        post_id = int(message.text)
        # Kiritilgan post_id mavjudligini tekshirish
        existing_kino = kino_db.search_kino_by_post_id(post_id)
        if existing_kino:
            await message.answer("Bu kod bilan kino allaqachon mavjud. Iltimos, boshqa kod kiriting.")
            return

        async with state.proxy() as data:
            data['post_id'] = post_id
            kino_db.add_kino(post_id=data['post_id'], file_id=data['file_id'], caption=data['caption'])

        await message.answer("Kino muvaffaqiyatli qo‘shildi.")
        await state.finish()

        # Yangi kino qo‘shilganda foydalanuvchilarga xabar yuborish
        await notify_users_about_new_kino(data['caption'])

    except ValueError:
        await message.answer("Iltimos kino kodni faqat raqam bilan yuboring.")

# Command to delete a kino (for admins)
@dp.message_handler(commands="kino_delete")
async def movie_delete_handler(message: types.Message):
    admin_id = message.from_user.id
    if admin_id in ADMINS:
        await KinoDelete.kino_code.set()
        await message.answer("O'chirmoqchi bo'lgan kino kodini yuboring")
    else:
        await message.answer("Siz admin emassiz")

# Handler to search kino by code before delete
@dp.message_handler(state=KinoDelete.kino_code, content_types=types.ContentType.TEXT)
async def movie_kino_code(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['post_id'] = int(message.text)
        result = kino_db.search_kino_by_post_id(data['post_id'])
        if result:
            await message.answer_video(video=result['file_id'], caption=result['caption'])
        else:
            await message.answer(f"{data['post_id']} : kod bilan kino topilmadi")
    await KinoDelete.is_confirm.set()
    await message.answer("Quyidagilardan birini tanlang", reply_markup=menu_movie)

@dp.message_handler(state=KinoDelete.is_confirm, content_types=types.ContentType.TEXT)
async def movie_kino_delete(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['is_confirm'] = message.text
        if data['is_confirm'] == "✅Tasdiqlash":
            kino_db.delete_kino(data['post_id'])
            await message.answer("Kino muvaffaqiyatli o'chirildi", reply_markup=ReplyKeyboardRemove())  # Knopkalar olib tashlanadi
            await state.finish()  # Holatni tugatish
        elif data['is_confirm'] == "❌Bekor qilish":
            await message.answer("Bekor qilindi", reply_markup=ReplyKeyboardRemove())  # Knopkalar olib tashlanadi
            await state.finish()  # Holatni tugatish
        else:
            await message.answer("Iltimos quyidagi tugmalardan birini tanlang", reply_markup=menu_movie)

# Command to count total kinolar in the database (for admins)
@dp.message_handler(commands="count_kinos")
async def message_count_kino(message: types.Message):
    count = kino_db.count_kinos()
    admin_id = message.from_user.id
    if admin_id in ADMINS:
        await message.answer(f"Bazada {count['count']} ta kino bor")
    else:
        await message.answer("Siz admin emassiz")

# Handler to search kino by post id (user side)
@dp.message_handler(lambda x: x.text.isdigit())
async def search_kino_handler(message: types.Message):
    if message.text.isdigit():
        post_id = int(message.text)
        data = kino_db.search_kino_by_post_id(post_id)
        if data:
            try:
                # Send the video to the user
                await bot.send_video(
                    chat_id=message.from_user.id,
                    video=data['file_id'],
                    caption=f"{data['caption']} \n\nKinoni Yuklanishlar Soni: {data['count_download']} \n\nKo'proq kinolar uchun biz bilan qoling"
                )

                # Update the download count in the database
                kino_db.update_download_count(post_id)
            except Exception as err:
                await message.answer(f"Kino topildi lekin yuborishda xatolik: {err}")
        else:
            await message.answer(f"{post_id} kod bilan kino topilmadi")
    else:
        await message.answer("Iltimos kino kodini raqam bilan yuboring")

# Handler to search kino by caption (user side)
@dp.message_handler(lambda msg: not msg.text.startswith("/"))
async def search_kino_by_caption_handler(message: types.Message):
    query = message.text.strip()
    kinolar = kino_db.search_kino_by_caption(query)
    if not query:
        await message.answer("Iltimos, kino izlash uchun tavsif kiriting.")
        return
    if kinolar:
        for file_id, caption in kinolar:
            await message.answer_video(video=file_id, caption=caption)
    else:
        await message.answer(f"'{query}' tavsifi bilan hech qanday kino topilmadi.")

# Foydalanuvchilarga yangi kino haqida xabar yuborish
async def notify_users_about_new_kino(caption):
    users = user_db.select_all_users()
    sent_count = 0
    error_count = 0

    for user_id in users:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"🎬 Yangi kino qo‘shildi:\n\n{caption}\n\nBarcha kinolarni ko‘rish uchun botga o'ting."
            )
            sent_count += 1
        except Exception as e:
            print(f"Xato foydalanuvchi {user_id} uchun: {e}")
            user_db.delete_user(user_id)
            error_count += 1
        await asyncio.sleep(0.1)

    print(f"Xabar {sent_count} foydalanuvchiga yuborildi, {error_count} ta xatolik yuz berdi.")


# Har qanday buyruq orqali holatdan chiqish
@dp.message_handler(state="*", commands=["start", "help", "kino_add", "kino_delete", "count_users", "count_kinos", "stats", "new_kinos"])
@dp.message_handler(lambda message: message.text.lower() in ["bekor qilish", "/cancel"], state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    # Holatdan chiqish
    await state.finish()
    await message.answer("Jarayon bekor qilindi. Siz bosh menyudasiz.", reply_markup=ReplyKeyboardRemove())
