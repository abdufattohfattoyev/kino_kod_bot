from datetime import datetime
from aiogram import types
from aiogram.dispatcher.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from data.config import ADMINS
from keyboards.default.kanal_button import kanal_keyboard
from loader import dp, bot, user_db, channel_db, kino_db, join_request_db
import asyncio
import logging

logger = logging.getLogger(__name__)


# Kanalda obuna tekshirish
async def check_subscription(user_id: int, channel_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception as e:
        logger.error(f"Kanal {channel_id} da {user_id} tekshirishda xatolik: {e}")

    # Join request yuborgan bo'lsa ham obuna hisoblanadi
    return join_request_db.has_request(user_id, channel_id)


# Barcha kanallarga obuna tekshiruvi
async def is_subscribed_to_all_channels(user_id: int) -> bool:
    channels = channel_db.get_all_channels()
    if not channels:
        return True  # Kanallar bo'sh bo'lsa, obuna talab qilinmaydi
    for channel_id, _, _ in channels:
        if not await check_subscription(user_id, channel_id):
            return False
    return True


# Obuna bo'lmagan kanallar ro'yxati
async def get_unsubscribed_channels(user_id: int) -> list:
    channels = channel_db.get_all_channels()
    if not channels:
        return []  # Agar kanallar bo'sh bo'lsa, bo'sh ro'yxat qaytaramiz
    return [(link, title) for channel_id, title, link in channels if not await check_subscription(user_id, channel_id)]


# Inline klaviatura
def get_subscription_keyboard(unsubscribed_channels):
    markup = InlineKeyboardMarkup(row_width=1)
    if unsubscribed_channels:  # Faqat ro'yxat bo'sh bo'lmasa tugma qo'shamiz
        for index, (invite_link, title) in enumerate(unsubscribed_channels, start=1):
            if invite_link.startswith("https://t.me/"):
                markup.add(InlineKeyboardButton(f"{index}. ➕ Obuna bo'lish)", url=invite_link))
            else:
                markup.add(InlineKeyboardButton(f"{index}. ➕ Obuna bo'lish", callback_data="no_action"))
        markup.add(InlineKeyboardButton("✅ Azo bo'ldim", callback_data="check_subscription"))
    return markup


# Qolgan kanallar haqida xabar
def get_remaining_channels_message(remaining_count):
    if remaining_count == 0:
        return "🎉 Barcha kanallarga obuna bo'ldingiz!"
    else:
        return f"📌 Hali {remaining_count} ta kanalga obuna bo'lishingiz kerak!"


# Avtomatik tekshirish va yangilash funksiyasi
async def auto_check_subscription(user_id: int, message: types.Message):
    from aiogram.utils.exceptions import MessageNotModified, MessageToEditNotFound, BadRequest
    while True:
        await asyncio.sleep(5)
        try:
            if await is_subscribed_to_all_channels(user_id):
                new_text = f"👋 Assalomu alaykum, {message.from_user.full_name}! Kino Botga xush kelibsiz.\n\n✍🏻 Kino kodini yuboring."
                try:
                    await message.edit_text(new_text, parse_mode="HTML")
                except (MessageNotModified, MessageToEditNotFound, BadRequest):
                    pass
                break
            else:
                unsubscribed = await get_unsubscribed_channels(user_id)
                new_text = "⚠️ <b>Siz hali barcha kanallarga obuna bo'lmadingiz!</b>\n\n👇 Quyidagilarga obuna bo'ling:"
                new_reply_markup = get_subscription_keyboard(unsubscribed)
                try:
                    await message.edit_text(new_text, reply_markup=new_reply_markup, parse_mode="HTML")
                except (MessageNotModified, MessageToEditNotFound, BadRequest):
                    pass
        except Exception as e:
            logger.error(f"auto_check_subscription xatolik: {e}")
            break


# Foydalanuvchini ro'yxatdan o'tkazish uchun alohida funksiya
async def register_user(user_id: int, username: str, context: str = "unknown") -> bool:
    try:
        if not user_db.select_user(user_id):
            user_db.add_user(user_id, username)
            user_count = user_db.count_users()
            logger.info(f"Yangi foydalanuvchi: @{username}, Jami: {user_count}, Context: {context}")


            # Adminlarga batafsil xabar yuborish
            for admin in ADMINS:
                try:
                    # Foydalanuvchi haqida qo'shimcha ma'lumot olish
                    user_info = await bot.get_chat(user_id)
                    full_name = user_info.full_name if user_info.full_name else "Noma'lum"
                    join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Ro'yxatdan o'tgan vaqt

                    # Chiroyli va to'liq xabar
                    admin_message = (
                        "🔔 <b>Yangi foydalanuvchi qo'shildi!</b>\n\n"
                        f"👤 <b>Username:</b> @{username}\n"
                        f"📛 <b>Ism:</b> {full_name}\n"
                        f"🆔 <b>ID:</b> {user_id}\n"
                        f"📅 <b>Ro'yxatdan o'tgan vaqt:</b> {join_date}\n"
                        f"👥 <b>Jami foydalanuvchilar:</b> {user_count}\n"
                        f"📍 <b>Kirish usuli:</b> {context}\n"
                        "────────────────────\n"
                        "<i>Botdan foydalanish boshlandi!</i>"
                    )
                    await bot.send_message(admin, admin_message, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Admin {admin} ga xabar yuborishda xatolik: {e}")
            return True
        else:
            user_db.update_last_active(user_id)
            logger.info(f"Foydalanuvchi {user_id} faolligi yangilandi, Context: {context}")
            return False
    except Exception as e:
        logger.error(f"Ro'yxatdan o'tkazishda xatolik (Context: {context}): {e}")
        raise


# /start komandasi (deep link: /start 12345)
@dp.message_handler(CommandStart())
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    logger.info(f"/start from user_id={user_id}, username={username}")

    if message.chat.type != "private":
        await message.reply("Bot faqat shaxsiy chatda ishlaydi!")
        return

    # Admin tekshiruvi
    if user_id in ADMINS:
        await message.answer(
            f"👑 Admin {message.from_user.full_name}! Botga xush kelibsiz.\n✍🏻 Kino kodini yuboring.",
            reply_markup=kanal_keyboard
        )
        # Deep link bo'lsa adminga ham kinoni yuboramiz
        args = message.get_args()
        if args and args.isdigit():
            from handlers.users.kino_handler import _send_kino
            await _send_kino(user_id, int(args))
        return

    # Foydalanuvchini ro'yxatdan o'tkazish (xabar yuborilmaydi)
    try:
        await register_user(user_id, username, context="/start")
    except Exception as e:
        logger.error(f"/start da ro'yxatdan o'tkazishda xatolik: {e}")
        await message.answer("⚠️ Ro'yxatdan o'tishda xatolik yuz berdi. Qayta urinib ko'ring.")
        return

    # Deep link argumentini saqlaymiz
    args = message.get_args()
    deep_link_post_id = int(args) if args and args.isdigit() else None

    # Kanallar ro'yxatini tekshirish
    channels = channel_db.get_all_channels()
    if not channels:  # Agar kanal bo'lmasa
        await message.answer(
            f"👋 Assalomu alaykum, {message.from_user.full_name}! Kino Botga xush kelibsiz.\n\n✍🏻 Kino kodini yuboring.",
            reply_markup=kanal_keyboard
        )
        if deep_link_post_id:
            from handlers.users.kino_handler import _send_kino
            await _send_kino(user_id, deep_link_post_id)
    else:  # Agar kanallar bo'lsa, obuna tekshiruvi
        if await is_subscribed_to_all_channels(user_id):
            await message.answer(
                f"👋 Assalomu alaykum, {message.from_user.full_name}! Kino Botga xush kelibsiz.\n\n✍🏻 Kino kodini yuboring.",
                reply_markup=kanal_keyboard
            )
            if deep_link_post_id:
                from handlers.users.kino_handler import _send_kino
                await _send_kino(user_id, deep_link_post_id)
        else:
            unsubscribed = await get_unsubscribed_channels(user_id)
            text = "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>"
            markup = get_subscription_keyboard(unsubscribed)
            # Deep link post_id ni saqlaymiz (obunadan keyin yuboramiz)
            if deep_link_post_id:
                from handlers.users.pending import pending_messages
                pending_messages[user_id] = {"post_id": deep_link_post_id}
            try:
                msg = await message.answer(text, reply_markup=markup, parse_mode="HTML")
                if unsubscribed:
                    asyncio.create_task(auto_check_subscription(user_id, msg))
            except Exception as e:
                logger.error(f"Obuna xabarini yuborishda xatolik: {e}")
                await message.answer("Xatolik yuz berdi. Qayta urinib ko'ring.")


# Obuna tekshirish callback
@dp.callback_query_handler(lambda c: c.data == "check_subscription")
async def check_subscription_callback(callback: types.CallbackQuery):
    from handlers.users.pending import pending_messages

    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.full_name

    if user_id in ADMINS:
        await callback.message.edit_text("👑 Siz adminsiz, obuna shart emas!", parse_mode="HTML")
        await callback.answer()
        return

    # Ikkinchi ro'yxatdan o'tkazish imkoniyati (xabar yuborilmaydi)
    try:
        await register_user(user_id, username, context="check_subscription")
    except Exception as e:
        await callback.message.edit_text("⚠️ Ro'yxatdan o'tishda xatolik yuz berdi. Qayta urinib ko'ring.", parse_mode="HTML")
        await callback.answer()
        return

    from aiogram.utils.exceptions import MessageNotModified, BadRequest

    # Obuna tekshiruvi
    if await is_subscribed_to_all_channels(user_id):
        try:
            await callback.message.edit_text(
                f"👋 Assalomu Alaykum, {callback.from_user.full_name}! Kino Botga xush kelibsiz.\n\n✍🏻 Kino kodini yuboring.",
                parse_mode="HTML"
            )
        except (MessageNotModified, BadRequest):
            pass
        await callback.answer()

        # Kutayotgan xabar bor bo'lsa qayta ishlaymiz
        pending = pending_messages.pop(user_id, None)
        if pending:
            if pending.get("is_forward"):
                await _process_pending_forward(user_id, pending)
            elif pending.get("post_id"):
                from handlers.users.kino_handler import _send_kino
                await _send_kino(user_id, pending["post_id"])
    else:
        unsubscribed = await get_unsubscribed_channels(user_id)
        text = "⚠️ <b>Hali barcha kanallarga obuna bo'lmadingiz!</b>\n\n👇 Quyidagilarga obuna bo'ling:"
        markup = get_subscription_keyboard(unsubscribed)
        try:
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except (MessageNotModified, BadRequest):
            pass
        await callback.answer("Obunani tekshiring!")


async def _process_pending_forward(user_id: int, pending: dict):
    """Obuna bo'lgandan keyin kutayotgan forwardni qayta ishlaydi."""
    forward_chat_id = pending.get("forward_from_chat_id")
    forward_msg_id = pending.get("forward_from_message_id")
    text = pending.get("text")

    # Agar original kanal va xabar ID mavjud bo'lsa - to'g'ridan-to'g'ri forward qilamiz
    if forward_chat_id and forward_msg_id:
        try:
            await bot.forward_message(
                chat_id=user_id,
                from_chat_id=forward_chat_id,
                message_id=forward_msg_id
            )
            return
        except Exception:
            pass  # Forward qilib bo'lmasa, matn orqali urinamiz

    # Matn raqam bo'lsa - kino qidiruvini ishga tushiramiz
    if text and text.strip().isdigit():
        from handlers.users.kino_handler import _send_kino
        try:
            await _send_kino(user_id, int(text.strip()))
        except Exception as e:
            logger.error(f"Pending forward kino yuborishda xatolik: {e}")
    elif text:
        # Boshqa matnli xabar bo'lsa - shunchaki yuborib beramiz
        await bot.send_message(
            chat_id=user_id,
            text=f"📨 <b>Saqlangan xabaringiz:</b>\n\n{text}",
            parse_mode="HTML"
        )


# "📽 Barcha kinolar" tugmasi
@dp.message_handler(lambda message: message.text == "📽 Barcha kinolar")
async def send_channel_link(message: types.Message):
    await message.answer(
        "<b>🎬 Yangi kinolar:</b>\n📌 https://t.me/Kino_mania_2026",
        parse_mode="HTML"
    )


# "🎲 Tasodifiy Kino" tugmasi
@dp.message_handler(text="🎲 Tasodifiy Kino")
async def random_kino_handler(message: types.Message):
    kino = kino_db.get_random_kino()
    if not kino:
        await message.answer("📭 Hozircha kinolar bazasi bo'sh.")
        return
    await message.answer("🎲 <b>Tasodifiy kino yuborilmoqda...</b>", parse_mode="HTML")
    from handlers.users.kino_handler import _send_kino
    await _send_kino(message.from_user.id, kino["post_id"])


def _extract_title(caption: str, post_id: int) -> str:
    """Caption dan faqat kino nomini oladi (birinchi mazmunli qator)."""
    if not caption:
        return f"Kino #{post_id}"
    for line in caption.split('\n'):
        line = line.strip()
        if line and not all(c in '➖━—─' for c in line):
            title = line[:40]
            return (title + "…") if len(line) > 40 else title
    return f"Kino #{post_id}"


# "🏆 Top 10 Kino" tugmasi
@dp.message_handler(text="🏆 Top 10 Kino")
async def top10_kino_handler(message: types.Message):
    tops = kino_db.get_top_kinos(10)
    if not tops:
        await message.answer("📭 Hozircha kinolar bazasi bo'sh.")
        return

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    markup = types.InlineKeyboardMarkup(row_width=1)
    lines = ["🏆 <b>Eng ko'p yuklab olingan 10 ta kino:</b>\n"]

    for i, (post_id, caption, count) in enumerate(tops, 1):
        medal = medals.get(i, f"{i}.")
        title = _extract_title(caption, post_id)
        lines.append(f"{medal} <b>{title}</b> — 📥 {count}")
        markup.add(types.InlineKeyboardButton(
            f"{medal} {title}",
            callback_data=f"kino_{post_id}"
        ))

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=markup)


# Shaxsiy kanal uchun no_action callback
@dp.callback_query_handler(lambda c: c.data == "no_action")
async def no_action_callback(callback: types.CallbackQuery):
    await callback.answer("Bu shaxsiy kanal. Iltimos, kanal adminidan tasdiq so'rang.", show_alert=True)
