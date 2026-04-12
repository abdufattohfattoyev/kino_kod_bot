import logging

from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.utils.exceptions import MessageNotModified

from data.config import ADMINS
from handlers.users.start import get_subscription_keyboard, is_subscribed_to_all_channels, get_unsubscribed_channels
from handlers.users.pending import pending_messages
from loader import bot, user_db

logger = logging.getLogger(__name__)

# /start va check_subscription - bular middlewareda bloklanmasin
ALLOWED_COMMANDS = {"/start"}
ALLOWED_CALLBACKS = {"check_subscription", "no_action"}


def _is_forward(msg: types.Message) -> bool:
    """Xabar forward ekanligini tekshiradi (barcha holatlar)."""
    return bool(
        msg.forward_from
        or msg.forward_from_chat
        or msg.forward_sender_name  # anonim foydalanuvchilar
    )


class SubscriptionMiddleware(BaseMiddleware):
    async def on_pre_process_update(self, update: types.Update, data: dict):
        user_id = None
        message = None

        if update.message:
            # from_user None bo'lishi mumkin (kanal postlari) - bunday holatda o'tkazib yuboramiz
            if not update.message.from_user:
                return
            user_id = update.message.from_user.id
            message = update.message
        elif update.callback_query:
            if not update.callback_query.from_user:
                return
            user_id = update.callback_query.from_user.id
            message = update.callback_query.message

        if not user_id:
            return

        # Adminlar uchun tekshiruv yo'q
        if isinstance(ADMINS, list) and user_id in ADMINS:
            return

        # Bloklangan foydalanuvchi
        try:
            if user_db.is_user_blocked(user_id):
                if update.message:
                    try:
                        await bot.send_message(
                            user_id,
                            "🚫 <b>Siz botdan foydalanish huquqingiz bloklangan.</b>",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
                raise CancelHandler()
        except CancelHandler:
            raise
        except Exception as e:
            logger.error(f"Bloklash tekshirishda xatolik (user_id={user_id}): {e}")

        # /start va obuna callback lari bloklanmasin
        if update.message:
            if update.message.text and update.message.text.split()[0] in ALLOWED_COMMANDS:
                return
        if update.callback_query:
            if update.callback_query.data in ALLOWED_CALLBACKS:
                return

        # Obuna tekshiruvi
        try:
            subscribed = await is_subscribed_to_all_channels(user_id)
        except Exception as e:
            logger.error(f"Obuna tekshirishda xatolik (user_id={user_id}): {e}")
            subscribed = False

        if subscribed:
            return  # Obuna bor - o'tkazib yuboramiz

        # --- Obuna yo'q: forward bo'lsa saqlaymiz ---
        if update.message and _is_forward(update.message):
            msg = update.message
            pending_messages[user_id] = {
                "is_forward": True,
                "text": msg.text or msg.caption,
                "forward_from_chat_id": msg.forward_from_chat.id if msg.forward_from_chat else None,
                "forward_from_message_id": msg.forward_from_message_id,
            }
            forward_saved_text = (
                "⏳ <b>Xabaringiz saqlandi!</b>\n\n"
                "📌 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling.\n"
                "Obuna bo'lgach xabaringiz avtomatik ko'rsatiladi:"
            )
        else:
            forward_saved_text = None

        # Obuna tugmalarini ko'rsatamiz
        try:
            unsubscribed = await get_unsubscribed_channels(user_id)
        except Exception as e:
            logger.error(f"Obuna bo'lmagan kanallarni olishda xatolik: {e}")
            unsubscribed = []

        sub_text = "📌 <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>"
        markup = get_subscription_keyboard(unsubscribed)
        display_text = forward_saved_text or sub_text

        if message and message.chat.type == "private":
            if update.message:
                try:
                    await message.answer(display_text, reply_markup=markup, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Obuna xabarini yuborishda xatolik: {e}")
            elif update.callback_query:
                try:
                    await message.edit_text(sub_text, reply_markup=markup, parse_mode="HTML")
                except MessageNotModified:
                    pass
                except Exception:
                    try:
                        await bot.send_message(user_id, sub_text, reply_markup=markup, parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"Callback obuna xabarida xatolik: {e}")
        else:
            try:
                await bot.send_message(user_id, sub_text, reply_markup=markup, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Guruh/kanal obuna xabarida xatolik: {e}")

        raise CancelHandler()
