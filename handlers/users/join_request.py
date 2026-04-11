import logging
from aiogram import types
from handlers.users.pending import pending_messages
from handlers.users.start import (
    is_subscribed_to_all_channels,
    _process_pending_forward,
    register_user,
)
from loader import dp, bot, channel_db, join_request_db

logger = logging.getLogger(__name__)


async def _welcome_user(user_id: int, full_name: str):
    """Foydalanuvchiga xush kelibsiz xabari va pending forwardni qayta ishlash."""
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ <b>So'rovingiz qabul qilindi!</b>\n\n"
                f"👋 Assalomu alaykum, {full_name}! Kino Botga xush kelibsiz.\n"
                "✍🏻 Kino kodini yuboring."
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Xush kelibsiz xabarida xatolik (user={user_id}): {e}")

    # Saqlangan forward bo'lsa qayta ishlaymiz
    pending = pending_messages.pop(user_id, None)
    if pending and pending.get("is_forward"):
        await _process_pending_forward(user_id, pending)


@dp.chat_join_request_handler()
async def handle_join_request(request: types.ChatJoinRequest):
    """Foydalanuvchi kanalga qo'shilish so'rovi yuborganda."""
    user_id = request.from_user.id
    channel_id = request.chat.id

    # Faqat bizning majburiy obuna kanallariga tegishli so'rovlarni saqlaymiz
    our_channels = {ch[0] for ch in channel_db.get_all_channels()}
    if channel_id not in our_channels:
        return

    # So'rovni DBga saqlaymiz
    join_request_db.add(user_id, channel_id)
    logger.info(f"Join request saqlandi: user={user_id}, channel={channel_id}")

    # Foydalanuvchini ro'yxatdan o'tkazamiz (agar yangi bo'lsa)
    username = request.from_user.username or request.from_user.full_name
    try:
        await register_user(user_id, username, context="join_request")
    except Exception:
        pass

    # Barcha kanallarga so'rov/obuna bo'ldimi?
    if await is_subscribed_to_all_channels(user_id):
        await _welcome_user(user_id, request.from_user.full_name)


@dp.chat_member_handler()
async def handle_chat_member_updated(update: types.ChatMemberUpdated):
    """Admin join requestni tasdiqlaganda yoki foydalanuvchi kanalga qo'shilganda."""
    user_id = update.from_user.id
    channel_id = update.chat.id
    new_status = update.new_chat_member.status
    old_status = update.old_chat_member.status

    # Faqat bizning kanallarimizga tegishli
    our_channels = {ch[0] for ch in channel_db.get_all_channels()}
    if channel_id not in our_channels:
        return

    # Foydalanuvchi member bo'ldi (join request tasdiklandi yoki o'zi qo'shildi)
    if new_status in ("member", "administrator") and old_status not in ("member", "administrator", "creator"):
        # join_requests dan o'chiramiz (endi haqiqiy member)
        join_request_db.remove(user_id, channel_id)
        logger.info(f"Member bo'ldi: user={user_id}, channel={channel_id}")

    # Foydalanuvchi chiqib ketdi yoki kicklandi - join requestni ham o'chiramiz
    elif new_status in ("left", "kicked"):
        join_request_db.remove(user_id, channel_id)
        logger.info(f"Kanaldan chiqdi: user={user_id}, channel={channel_id}")
