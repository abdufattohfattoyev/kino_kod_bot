from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Command
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import logging
from data.config import ADMINS, update_env_admins
from handlers.users.middleware import SubscriptionMiddleware
from handlers.users.reklama import ReklamaTuriState
from handlers.users.start import is_subscribed_to_all_channels, get_unsubscribed_channels, get_subscription_keyboard
from loader import dp, bot, kino_db, user_db, channel_db, join_request_db
from keyboards.default.button_kino import menu_movie
from keyboards.default.admin_menu import admin_menu

# Logging sozlamasi
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Middleware ni sozlash
def setup_subscription_middleware():
    dp.middleware.setup(SubscriptionMiddleware())

# States for kino add and delete
class KinoAdd(StatesGroup):
    kino_add   = State()   # 1-qism (yoki yagona) video kutish
    more_parts = State()   # "Yana qism?" savoli
    kino_code  = State()   # Kod kiritish

class KinoDelete(StatesGroup):
    kino_code = State()
    is_confirm = State()

class KinoPartAdd(StatesGroup):
    enter_code  = State()   # Qaysi kino? Kod so'raymiz
    enter_video = State()   # Video qabul qilamiz
    ask_more    = State()   # Yana qism?

# States for admin add and remove
class AdminAdd(StatesGroup):
    telegram_id = State()

class AdminRemove(StatesGroup):
    telegram_id = State()
    is_confirm = State()

# Asosiy adminni tekshirish funksiyasi
def is_main_admin(user_id: int):
    """Faqat birinchi admin (ADMINS[0]) asosiy admin hisoblanadi."""
    return user_id == ADMINS[0] if ADMINS else False

# Admin paneli
@dp.message_handler(Command("admin"))
async def admin_panel(message: types.Message):
    if user_db.check_if_admin(message.from_user.id) or message.from_user.id in ADMINS:
        await message.answer("Admin paneliga xush kelibsiz! Kerakli bo‘limni tanlang:", reply_markup=admin_menu)
    else:
        await message.answer("🚫 Siz admin emassiz.")

# Statistika ko‘rish
def _build_bar(value: int, max_value: int, width: int = 10) -> str:
    """Oddiy matnli progress bar."""
    if max_value == 0:
        filled = 0
    else:
        filled = round(value / max_value * width)
    return "█" * filled + "░" * (width - filled)


def _build_main_stats() -> str:
    kinos_raw = kino_db.count_kinos()
    # count_kinos() dict qaytarishi mumkin — ikkalasini ham qo'llab-quvvatlaymiz
    total_kinos = kinos_raw.get("Jami Kinolar", 0) if isinstance(kinos_raw, dict) else kinos_raw

    total_users   = user_db.count_users()
    daily_users   = user_db.count_daily_users()
    weekly_users  = user_db.count_weekly_users()
    monthly_users = user_db.count_monthly_users()
    active_daily  = user_db.count_active_daily_users()
    active_weekly = user_db.count_active_weekly_users()
    active_monthly= user_db.count_active_monthly_users()
    passive       = user_db.count_passive_users(days=30)

    active_pct = round(active_monthly / total_users * 100) if total_users else 0
    passive_pct= round(passive / total_users * 100) if total_users else 0

    return (
        "📊 <b>Bot statistikasi</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎬 Kinolar bazasi:     <b>{kinos}</b> ta\n"
        "👥 Jami foydalanuvchi: <b>{total}</b> ta\n"
        "✅ Faol (oylik):       <b>{m_act}</b> ta ({act_pct}%)\n"
        "💤 Passiv (30+ kun):   <b>{passive}</b> ta ({pas_pct}%)\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🗓 <b>Bugun</b>\n"
        "   ➕ Yangi: <b>{d_new}</b>    •    🟢 Faol: <b>{d_act}</b>\n"
        "📅 <b>Hafta</b>\n"
        "   ➕ Yangi: <b>{w_new}</b>    •    🟢 Faol: <b>{w_act}</b>\n"
        "📆 <b>Oy</b>\n"
        "   ➕ Yangi: <b>{m_new}</b>    •    🟢 Faol: <b>{m_act}</b>"
    ).format(
        kinos=total_kinos, total=total_users,
        passive=passive, act_pct=active_pct, pas_pct=passive_pct,
        d_new=daily_users,   d_act=active_daily,
        w_new=weekly_users,  w_act=active_weekly,
        m_new=monthly_users, m_act=active_monthly,
    )


def _build_top10() -> str:
    tops = kino_db.get_top_kinos(10)
    if not tops:
        return "📭 Hozircha kinolar yo’q."
    lines = ["🏆 <b>Eng ko’p yuklab olingan 10 ta kino</b>\n━━━━━━━━━━━━━━━━━"]
    for i, (post_id, caption, count) in enumerate(tops, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        short = (caption[:30] + "…") if caption and len(caption) > 30 else (caption or "—")
        lines.append(f"{medal} <b>{short}</b>\n    📥 {count} marta | kod: <code>{post_id}</code>")
    return "\n".join(lines)


def _build_growth() -> str:
    rows = user_db.get_daily_growth(days=7)
    if not rows:
        return "📭 Ma’lumot yo’q."
    max_cnt = max(cnt for _, cnt in rows) if rows else 1
    lines = ["📈 <b>So’nggi 7 kun — yangi foydalanuvchilar</b>\n━━━━━━━━━━━━━━━━━"]
    for day, cnt in rows:
        bar = _build_bar(cnt, max_cnt, width=12)
        lines.append(f"<code>{day[5:]}</code>  {bar}  <b>{cnt}</b>")
    total = sum(cnt for _, cnt in rows)
    lines.append(f"━━━━━━━━━━━━━━━━━\nJami 7 kunda: <b>{total}</b> ta yangi foydalanuvchi")
    return "\n".join(lines)


def _stats_markup(page: str = "main") -> InlineKeyboardMarkup:
    btn_top = InlineKeyboardButton("🏆 Top-10", callback_data="stats_top10")
    btn_growth = InlineKeyboardButton("📈 O’sish", callback_data="stats_growth")
    btn_main = InlineKeyboardButton("📊 Asosiy", callback_data="stats_main")
    btn_refresh = InlineKeyboardButton("🔄 Yangilash", callback_data="refresh_stats")

    markup = InlineKeyboardMarkup(row_width=2)
    if page == "main":
        markup.add(btn_top, btn_growth)
        markup.add(btn_refresh)
    elif page == "top10":
        markup.add(btn_main, btn_growth)
        markup.add(btn_refresh)
    elif page == "growth":
        markup.add(btn_main, btn_top)
        markup.add(btn_refresh)
    return markup


@dp.message_handler(text="📊 Statistika")
async def show_stats(message: types.Message):
    if not user_db.check_if_admin(message.from_user.id) and message.from_user.id not in ADMINS:
        await message.answer("🚫 <b>Siz admin emassiz.</b>", parse_mode="HTML")
        return
    try:
        await message.answer(_build_main_stats(), parse_mode="HTML", reply_markup=_stats_markup("main"))
    except Exception as e:
        await message.answer("❌ Statistika olishda xatolik.", parse_mode="HTML")
        logger.error(f"show_stats xatolik: {e}")


@dp.callback_query_handler(lambda c: c.data in ("refresh_stats", "stats_main", "stats_top10", "stats_growth"))
async def stats_callback(callback: types.CallbackQuery):
    if not user_db.check_if_admin(callback.from_user.id) and callback.from_user.id not in ADMINS:
        await callback.answer("🚫 Siz admin emassiz.", show_alert=True)
        return

    action = callback.data
    if action in ("refresh_stats", "stats_main"):
        # Progress bar ko’rsatamiz
        for stage in ["◦◦◦◦◦", "●◦◦◦◦", "●●◦◦◦", "●●●◦◦", "●●●●◦"]:
            try:
                await callback.message.edit_text(
                    f"✨ <b>Yangilanmoqda</b>  |{stage}|", parse_mode="HTML"
                )
            except Exception:
                pass
            await asyncio.sleep(0.4)
        text = _build_main_stats()
        markup = _stats_markup("main")
        page = "main"
    elif action == "stats_top10":
        text = _build_top10()
        markup = _stats_markup("top10")
        page = "top10"
    else:  # stats_growth
        text = _build_growth()
        markup = _stats_markup("growth")
        page = "growth"

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        await callback.answer("✅ Yangilandi!" if action == "refresh_stats" else "")
    except Exception as e:
        logger.error(f"stats_callback xatolik ({action}): {e}")
        await callback.answer()

# Admin qo‘shish (faqat asosiy admin uchun)
@dp.message_handler(text="👤 Admin Qo‘shish")
async def admin_add_start(message: types.Message, state: FSMContext):
    if not is_main_admin(message.from_user.id):
        await message.answer("🚫 Faqat asosiy admin yangi admin qo‘sha oladi.")
        return
    await AdminAdd.telegram_id.set()
    await message.answer("👤 Yangi adminning Telegram ID sini kiriting:")

@dp.message_handler(state=AdminAdd.telegram_id, content_types=types.ContentType.TEXT)
async def admin_add_id(message: types.Message, state: FSMContext):
    if message.text == "🔙 Admin menyu":
        await state.finish()
        await message.answer("Jarayon bekor qilindi. Siz bosh menyudasiz.", reply_markup=admin_menu)
        return

    try:
        telegram_id = int(message.text)
        user = user_db.select_user(telegram_id)
        if not user:
            await message.answer("❌ Bu Telegram ID bilan foydalanuvchi topilmadi. Foydalanuvchi bot bilan suhbat boshlagan bo‘lishi kerak.")
            return
        if user_db.check_if_admin(telegram_id) or telegram_id in ADMINS:
            await message.answer("⚠️ Bu foydalanuvchi allaqachon admin.")
            return

        user_db.set_admin(telegram_id)
        if telegram_id not in ADMINS:
            ADMINS.append(telegram_id)
            try:
                update_env_admins(ADMINS)
                logger.info(f"Admin {telegram_id} added successfully.")
            except Exception as e:
                logger.warning(f".env yangilashda xatolik (lekin DB da saqlandi): {e}")
        await message.answer(f"✅ Foydalanuvchi (ID: {telegram_id}) admin sifatida qo’shildi.")
        try:
            await bot.send_message(telegram_id, "🎉 Siz botning admini sifatida qo‘shildingiz!")
        except Exception as e:
            logger.error(f"Failed to notify new admin {telegram_id}: {e}")
        await state.finish()
        await message.answer("Admin menyusiga qaytish uchun tugmani bosing:", reply_markup=admin_menu)
    except ValueError:
        await message.answer("❌ Iltimos, Telegram ID ni faqat raqam shaklida kiriting.")

# Admin o‘chirish (faqat asosiy admin uchun)
@dp.message_handler(text="🗑 Admin O‘chirish")
async def admin_remove_start(message: types.Message, state: FSMContext):
    if not is_main_admin(message.from_user.id):
        await message.answer("🚫 Faqat asosiy admin adminlarni o‘chira oladi.")
        return
    await AdminRemove.telegram_id.set()
    await message.answer("🗑 O‘chirmoqchi bo‘lgan adminning Telegram ID sini kiriting:")

@dp.message_handler(state=AdminRemove.telegram_id, content_types=types.ContentType.TEXT)
async def admin_remove_id(message: types.Message, state: FSMContext):
    if message.text == "🔙 Admin menyu":
        await state.finish()
        await message.answer("Jarayon bekor qilindi. Siz bosh menyudasiz.", reply_markup=admin_menu)
        return

    try:
        telegram_id = int(message.text)
        if telegram_id == message.from_user.id:
            await message.answer("❌ O‘zingizni adminlikdan o‘chira olmaysiz.")
            return
        user = user_db.select_user(telegram_id)
        if not user:
            await message.answer("❌ Bu Telegram ID bilan foydalanuvchi topilmadi.")
            return
        if not user_db.check_if_admin(telegram_id) and telegram_id not in ADMINS:
            await message.answer("⚠️ Bu foydalanuvchi admin emas.")
            return

        async with state.proxy() as data:
            data['telegram_id'] = telegram_id
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Tasdiqlash", callback_data="confirm_remove_admin"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_remove_admin")
        )
        await message.answer(
            f"🗑 Foydalanuvchi (ID: {telegram_id}, Username: {user[2] or 'N/A'}) adminlikdan o‘chirilsinmi?",
            reply_markup=markup
        )
    except ValueError:
        await message.answer("❌ Iltimos, Telegram ID ni faqat raqam shaklida kiriting.")

@dp.callback_query_handler(lambda c: c.data in ["confirm_remove_admin", "cancel_remove_admin"], state=AdminRemove.telegram_id)
async def admin_remove_confirm(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        telegram_id = data['telegram_id']
    if callback.data == "confirm_remove_admin":
        user_db.remove_admin(telegram_id)
        if telegram_id in ADMINS:
            ADMINS.remove(telegram_id)
            try:
                update_env_admins(ADMINS)
                logger.info(f"Admin {telegram_id} removed successfully.")
            except Exception as e:
                logger.warning(f".env yangilashda xatolik (lekin DB da saqlandi): {e}")
        await callback.message.edit_text(f"✅ Foydalanuvchi (ID: {telegram_id}) adminlikdan o’chirildi.")
        try:
            await bot.send_message(telegram_id, "❌ Siz bot adminligidan olib tashlandiniz.")
        except Exception as e:
            logger.error(f"Failed to notify removed admin {telegram_id}: {e}")
    else:
        await callback.message.edit_text("❌ Jarayon bekor qilindi.")
    await state.finish()
    await callback.message.answer("Admin menyusiga qaytish uchun tugmani bosing:", reply_markup=admin_menu)
    await callback.answer()

# Adminlar ro‘yxatini ko‘rish (barcha adminlar uchun ruxsat berilgan)
@dp.message_handler(text="📋 Adminlar Ro‘yxati")
async def show_admins_list(message: types.Message):
    if not user_db.check_if_admin(message.from_user.id) and message.from_user.id not in ADMINS:
        await message.answer("🚫 Siz admin emassiz.")
        return
    try:
        admins = user_db.get_all_admins()
        if not admins:
            await message.answer("📋 Hozirda hech qanday admin yo‘q.")
            return
        admin_list = "\n".join([f"👤 ID: {admin[0]}, Username: {admin[1] or 'N/A'}" for admin in admins])
        await message.answer(f"📋 <b>Adminlar ro‘yxati:</b>\n{admin_list}", parse_mode="HTML")
    except Exception as e:
        await message.answer("❌ Adminlar ro‘yxatini olishda xatolik yuz berdi.")
        logger.error(f"Error fetching admins list: {e}")

# So’rovlar statistikasi
@dp.message_handler(text="📨 So’rovlar")
async def show_join_requests(message: types.Message):
    if not user_db.check_if_admin(message.from_user.id) and message.from_user.id not in ADMINS:
        await message.answer("🚫 Siz admin emassiz.")
        return

    total = join_request_db.total_count()
    counts = join_request_db.count_by_channel()  # [(channel_id, count), ...]
    channels = {ch[0]: ch[1] for ch in channel_db.get_all_channels()}  # {id: title}

    if total == 0:
        await message.answer("📭 Hozircha hech kim so’rov yuborgan emas.")
        return

    lines = [f"📨 <b>Jami so’rovlar: {total} ta</b>\n"]
    for channel_id, count in counts:
        title = channels.get(channel_id, f"Kanal {channel_id}")
        lines.append(f"📢 <b>{title}</b>\n👥 So’rovlar: <b>{count} ta</b>\n")

    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔄 Yangilash", callback_data="refresh_join_requests")
    )
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == "refresh_join_requests")
async def refresh_join_requests(callback: types.CallbackQuery):
    if not user_db.check_if_admin(callback.from_user.id) and callback.from_user.id not in ADMINS:
        await callback.answer("🚫 Siz admin emassiz.", show_alert=True)
        return

    total = join_request_db.total_count()
    counts = join_request_db.count_by_channel()
    channels = {ch[0]: ch[1] for ch in channel_db.get_all_channels()}

    if total == 0:
        await callback.message.edit_text("📭 Hozircha hech kim so’rov yuborgan emas.")
        await callback.answer()
        return

    lines = [f"📨 <b>Jami so’rovlar: {total} ta</b>\n"]
    for channel_id, count in counts:
        title = channels.get(channel_id, f"Kanal {channel_id}")
        lines.append(f"📢 <b>{title}</b>\n👥 So’rovlar: <b>{count} ta</b>\n")

    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔄 Yangilash", callback_data="refresh_join_requests")
    )
    try:
        await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=markup)
    except Exception:
        pass
    await callback.answer("✅ Yangilandi!")


# ── Kino qo’shish (ko’p qismli qo’llab-quvvatlash bilan) ─────────────────

def _more_parts_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton("➕ Ha, qo’shaman", callback_data="kino_add_more"),
        InlineKeyboardButton("✅ Tugatish", callback_data="kino_add_done"),
    )


@dp.message_handler(text="➕ Kino Qo’shish")
async def message_kino_add(message: types.Message, state: FSMContext):
    if not user_db.check_if_admin(message.from_user.id) and message.from_user.id not in ADMINS:
        await message.answer("🚫 Siz admin emassiz.")
        return
    await KinoAdd.kino_add.set()
    async with state.proxy() as data:
        data["parts"] = []       # file_id lar ro’yxati
        data["caption"] = ""
    await message.answer(
        "🎬 <b>1-qism videoni yuboring:</b>",
        parse_mode="HTML"
    )


@dp.message_handler(text="🔙 Admin menyu", state=KinoAdd.kino_add)
async def cancel_kino_add(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Jarayon bekor qilindi.", reply_markup=admin_menu)


# Video keldi — qismlar ro’yxatiga qo’shamiz
@dp.message_handler(state=KinoAdd.kino_add, content_types=types.ContentType.VIDEO)
async def kino_file_handler(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["parts"].append(message.video.file_id)
        if not data["caption"]:
            data["caption"] = message.caption or "Kino"
        part_num = len(data["parts"])

    await KinoAdd.more_parts.set()
    await message.answer(
        f"✅ <b>{part_num}-qism qabul qilindi.</b>\n\n"
        "Yana qism qo’shishni xohlaysizmi?",
        parse_mode="HTML",
        reply_markup=_more_parts_markup()
    )


# "Ha, qo’shaman" — keyingi qismni yuborish
@dp.callback_query_handler(lambda c: c.data == "kino_add_more", state=KinoAdd.more_parts)
async def kino_add_more(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        part_num = len(data["parts"]) + 1
    await KinoAdd.kino_add.set()
    await callback.message.edit_text(
        f"🎬 <b>{part_num}-qism videoni yuboring:</b>",
        parse_mode="HTML"
    )
    await callback.answer()


# "Tugatish" — kod kiritish bosqichi
@dp.callback_query_handler(lambda c: c.data == "kino_add_done", state=KinoAdd.more_parts)
async def kino_add_done(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        total = len(data["parts"])
    await KinoAdd.kino_code.set()
    await callback.message.edit_text(
        f"📦 Jami <b>{total} ta qism</b> tayyor.\n\n"
        "📎 <b>Kino uchun kod kiriting (raqam):</b>",
        parse_mode="HTML"
    )
    await callback.answer()


# Kod kiritildi — saqlaymiz
@dp.message_handler(state=KinoAdd.kino_code, content_types=types.ContentType.TEXT)
async def kino_code_handler(message: types.Message, state: FSMContext):
    if message.text == "🔙 Admin menyu":
        await state.finish()
        await message.answer("Jarayon bekor qilindi.", reply_markup=admin_menu)
        return

    try:
        post_id = int(message.text)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting.")
        return

    if kino_db.search_kino_by_post_id(post_id):
        await message.answer("⚠️ Bu kod bilan kino allaqachon mavjud. Boshqa kod kiriting.")
        return

    async with state.proxy() as data:
        parts   = data["parts"]
        caption = data["caption"]

    # Asosiy yozuv (birinchi part file_id bilan)
    kino_db.add_kino(post_id=post_id, file_id=parts[0], caption=caption)

    # Barcha qismlarni KinoParts ga saqlaymiz
    kino_db.add_parts(post_id=post_id, file_ids=parts)

    await state.finish()
    await message.answer(
        f"✅ <b>Kino qo’shildi!</b>\n"
        f"📦 Qismlar soni: <b>{len(parts)} ta</b>\n"
        f"🔑 Kod: <code>{post_id}</code>",
        parse_mode="HTML",
        reply_markup=admin_menu
    )

# ── Mavjud kinoga qism qo’shish ──────────────────────────────────────────

@dp.message_handler(text="🎬 Qism Qo’shish")
async def part_add_start(message: types.Message, state: FSMContext):
    if not user_db.check_if_admin(message.from_user.id) and message.from_user.id not in ADMINS:
        await message.answer("🚫 Siz admin emassiz.")
        return
    await KinoPartAdd.enter_code.set()
    await message.answer(
        "🔑 Qaysi kinoga qism qo’shmoqchisiz?\n"
        "<b>Kino kodini yuboring:</b>",
        parse_mode="HTML"
    )


@dp.message_handler(state=KinoPartAdd.enter_code, content_types=types.ContentType.TEXT)
async def part_add_code(message: types.Message, state: FSMContext):
    if message.text.strip() == "🔙 Admin menyu":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu)
        return

    if not message.text.strip().isdigit():
        await message.answer("❌ Faqat raqam kiriting.")
        return

    post_id = int(message.text.strip())
    kino = kino_db.search_kino_by_post_id(post_id)
    if not kino:
        await message.answer(f"⚠️ <b>{post_id}</b> kodi bilan kino topilmadi.", parse_mode="HTML")
        return

    current_parts = kino_db.count_parts(post_id)
    async with state.proxy() as data:
        data["post_id"] = post_id
        data["current_parts"] = current_parts

    await KinoPartAdd.enter_video.set()
    await message.answer(
        f"🎬 <b>{kino[‘caption’]}</b>\n"
        f"📦 Hozirda: <b>{current_parts} ta qism</b>\n\n"
        f"🎥 <b>{current_parts + 1}-qism videoni yuboring:</b>",
        parse_mode="HTML"
    )


@dp.message_handler(state=KinoPartAdd.enter_video, content_types=types.ContentType.VIDEO)
async def part_add_video(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        post_id = data["post_id"]

    new_part_num = kino_db.add_next_part(post_id=post_id, file_id=message.video.file_id)

    async with state.proxy() as data:
        data["current_parts"] = new_part_num

    await KinoPartAdd.ask_more.set()
    await message.answer(
        f"✅ <b>{new_part_num}-qism qo’shildi!</b>\n\n"
        "Yana qism qo’shishni xohlaysizmi?",
        parse_mode="HTML",
        reply_markup=_more_parts_markup()
    )


@dp.callback_query_handler(lambda c: c.data == "kino_add_more", state=KinoPartAdd.ask_more)
async def part_add_more(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        next_num = data["current_parts"] + 1
    await KinoPartAdd.enter_video.set()
    await callback.message.edit_text(
        f"🎥 <b>{next_num}-qism videoni yuboring:</b>",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data == "kino_add_done", state=KinoPartAdd.ask_more)
async def part_add_finish(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        post_id = data["post_id"]
        total = data["current_parts"]
    await state.finish()
    await callback.message.edit_text(
        f"✅ <b>Tayyor!</b>\n"
        f"🔑 Kod: <code>{post_id}</code>\n"
        f"📦 Jami qismlar: <b>{total} ta</b>",
        parse_mode="HTML"
    )
    await callback.message.answer("Admin menyu:", reply_markup=admin_menu)
    await callback.answer()


# Kino o’chirish
@dp.message_handler(text="🗑 Kino O’chirish")
async def movie_delete_handler(message: types.Message, state: FSMContext):
    if not user_db.check_if_admin(message.from_user.id) and message.from_user.id not in ADMINS:
        await message.answer("🚫 Siz admin emassiz.")
        return
    await KinoDelete.kino_code.set()
    await message.answer("🗑 O‘chirmoqchi bo‘lgan kino kodini yuboring")

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
            await message.answer("✅ Kino muvaffaqiyatli o‘chirildi", reply_markup=ReplyKeyboardRemove())
            await state.finish()
            await message.answer("Admin menyusiga qaytish uchun tugmani bosing:", reply_markup=admin_menu)
        elif data['is_confirm'] == "❌Bekor qilish":
            await message.answer("❌ Bekor qilindi", reply_markup=ReplyKeyboardRemove())
            await state.finish()
            await message.answer("Admin menyusiga qaytish uchun tugmani bosing:", reply_markup=admin_menu)
        else:
            await message.answer("Iltimos quyidagi tugmalardan birini tanlang", reply_markup=menu_movie)

# ── Kino qidirish (foydalanuvchi tarafi) ─────────────────────────────────

async def _send_kino(user_id: int, post_id: int, notify_not_found=True) -> bool:
    """Kinoni (yoki barcha qismlarini) foydalanuvchiga yuboradi. True → muvaffaqiyatli."""
    data = kino_db.search_kino_by_post_id(post_id)
    if not data:
        if notify_not_found:
            await bot.send_message(
                user_id,
                f"⚠️ <b>{post_id}</b> kodi bilan kino topilmadi.",
                parse_mode="HTML"
            )
        return False

    parts = kino_db.get_parts(post_id)

    caption_base = (
        "<b>" + str(data["caption"]) + "</b>\n\n"
        "📥 <b>Kino Yuklash Soni:</b> " + str(data["count_download"]) + "\n\n"
        "📌 <b>Barcha kinolar:</b> <b>T.me/Kino_Mania_2024</b>"
    )

    if len(parts) <= 1:
        # Yagona video
        await bot.send_video(
            chat_id=user_id,
            video=data["file_id"],
            caption=caption_base,
            parse_mode="HTML"
        )
    else:
        # Ko'p qismli — har bir qism alohida
        total = len(parts)
        for part_num, file_id in parts:
            if part_num == 1:
                cap = caption_base + f"\n\n🎬 <b>Qism {part_num}/{total}</b>"
            else:
                cap = f"🎬 <b>{data['caption']} — Qism {part_num}/{total}</b>"
            await bot.send_video(
                chat_id=user_id,
                video=file_id,
                caption=cap,
                parse_mode="HTML"
            )

    kino_db.update_download_count(post_id)
    return True


@dp.message_handler(lambda x: x.text and x.text.isdigit())
async def search_kino_handler(message: types.Message):
    user_id = message.from_user.id
    user_db.update_last_active(user_id)
    post_id = int(message.text)
    try:
        await _send_kino(user_id, post_id)
    except Exception as err:
        await message.answer(f"❌ Kino yuborishda xatolik: {err}", parse_mode="HTML")
        logger.error(f"search_kino_handler xatolik user={user_id}: {err}")

# ── Kalit so'z bilan qidirish ──────────────────────────────────────────────

# Qidiruv natijasini inline tugma sifatida ko'rsatish
def _search_markup(results: list) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    for post_id, caption, count in results:
        short = (caption[:35] + "…") if caption and len(caption) > 35 else (caption or f"#{post_id}")
        markup.add(InlineKeyboardButton(
            f"🎬 {short}  •  📥{count}",
            callback_data=f"kino_{post_id}"
        ))
    return markup


_KNOWN_BUTTONS = {
    "📽 Barcha kinolar", "➕ Kino Qo'shish", "📊 Statistika",
    "📣 Reklama", "🗑 Kino O'chirish", "👤 Admin Qo'shish",
    "🗑 Admin O'chirish", "📋 Adminlar Ro'yxati", "📨 So'rovlar",
    "📢 Kanallar", "🔙 Admin menyu", "✅Tasdiqlash", "❌Bekor qilish",
}


@dp.message_handler(
    lambda m: (
        m.text
        and not m.text.isdigit()
        and not m.text.startswith("/")
        and m.text not in _KNOWN_BUTTONS
        and len(m.text.strip()) >= 2
    )
)
async def search_by_caption_handler(message: types.Message):
    query = message.text.strip()
    results = kino_db.search_by_caption(query, limit=8)
    if not results:
        await message.answer(
            f"🔍 <b>«{query}»</b> bo'yicha hech narsa topilmadi.",
            parse_mode="HTML"
        )
        return
    await message.answer(
        f"🔍 <b>«{query}»</b> bo'yicha {len(results)} ta natija:\n"
        "👇 Kinoni tanlang:",
        parse_mode="HTML",
        reply_markup=_search_markup(results)
    )


@dp.callback_query_handler(lambda c: c.data.startswith("kino_") and c.data[5:].isdigit())
async def send_kino_by_callback(callback: types.CallbackQuery):
    post_id = int(callback.data.split("_", 1)[1])
    user_id = callback.from_user.id
    try:
        found = await _send_kino(user_id, post_id, notify_not_found=False)
        if found:
            user_db.update_last_active(user_id)
            await callback.answer()
        else:
            await callback.answer("❌ Kino topilmadi.", show_alert=True)
    except Exception as e:
        logger.error(f"send_kino_by_callback xatolik: {e}")
        await callback.answer("❌ Kino yuborishda xatolik.", show_alert=True)


# Bosh menyuga qaytish
@dp.message_handler(text="🔙 Admin menyu", state="*")
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await state.finish()
    if user_db.check_if_admin(message.from_user.id) or message.from_user.id in ADMINS:
        await message.answer("Jarayon bekor qilindi. Siz Admin menyudasiz.", reply_markup=admin_menu)
    else:
        await message.answer("Jarayon bekor qilindi.", reply_markup=ReplyKeyboardRemove())

# Bekor qilish handleri
@dp.message_handler(
    lambda message: message.text in [
        "➕ Kino Qo‘shish", "📊 Statistika", "📣 Reklama", "🗑 Kino O‘chirish",
        "👤 Admin Qo‘shish", "🗑 Admin O‘chirish", "📋 Adminlar Ro‘yxati"
    ], state="*")
@dp.message_handler(lambda message: message.text.lower() in ["bekor qilish", "/cancel"], state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.finish()
    if user_db.check_if_admin(message.from_user.id) or message.from_user.id in ADMINS:
        await message.answer("Jarayon bekor qilindi. Siz Admin menyudasiz.", reply_markup=admin_menu)
    else:
        await message.answer("Jarayon bekor qilindi.", reply_markup=ReplyKeyboardRemove())

# Middleware ni faollashtirish
setup_subscription_middleware()