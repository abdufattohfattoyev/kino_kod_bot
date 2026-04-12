import asyncio
import logging
import os
from datetime import datetime

from aiogram import types

from data.config import ADMINS
from loader import dp, bot, user_db

logger = logging.getLogger(__name__)

DB_FILES = [
    ("data/main.db",         "👥 Foydalanuvchilar DB"),
    ("data/kino.db",         "🎬 Kinolar DB"),
    ("data/channel.db",      "📢 Kanallar DB"),
    ("data/join_requests.db","📨 So'rovlar DB"),
]


def _is_admin(user_id: int) -> bool:
    return user_id in ADMINS or user_db.check_if_admin(user_id)


async def send_backup_to_admins(notify_text: str = None):
    """Barcha DB fayllarini barcha adminlarga yuboradi."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    caption_prefix = notify_text or f"💾 <b>Backup</b> — {now}"

    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, caption_prefix, parse_mode="HTML")
            for path, label in DB_FILES:
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        await bot.send_document(
                            admin_id,
                            f,
                            caption=f"📁 {label}",
                        )
                else:
                    await bot.send_message(admin_id, f"⚠️ {label} topilmadi: <code>{path}</code>", parse_mode="HTML")
        except Exception as e:
            logger.error(f"Admin {admin_id} ga backup yuborishda xatolik: {e}")


@dp.message_handler(text="💾 Backup")
async def manual_backup(message: types.Message):
    if not _is_admin(message.from_user.id):
        await message.answer("🚫 Siz admin emassiz.")
        return

    await message.answer("⏳ Backup tayyorlanmoqda...")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    await send_backup_to_admins(f"💾 <b>Manual Backup</b>\n📅 {now}\n👤 Admin: @{message.from_user.username or message.from_user.id}")
    await message.answer("✅ Backup barcha adminlarga yuborildi.")


async def auto_backup_loop():
    """Har kuni soat 03:00 da avtomatik backup."""
    while True:
        now = datetime.now()
        # Keyingi 03:00 ni hisoblash
        next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run = next_run.replace(day=next_run.day + 1)
        wait_seconds = (next_run - now).total_seconds()
        logger.info(f"Keyingi avtomatik backup: {next_run.strftime('%Y-%m-%d %H:%M')} ({int(wait_seconds)}s)")
        await asyncio.sleep(wait_seconds)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        await send_backup_to_admins(f"🤖 <b>Avtomatik Backup</b>\n📅 {now_str}")
        logger.info("Avtomatik backup yuborildi.")
