from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📊 Statistika"), KeyboardButton("➕ Kino Qo’shish")],
        [KeyboardButton("🗑 Kino O’chirish"), KeyboardButton("🎬 Qism Qo’shish")],
        [KeyboardButton("✏️ Kino Tahrirlash"), KeyboardButton("📣 Reklama")],
        [KeyboardButton("📢 Kanallar"), KeyboardButton("💾 Backup")],
        [KeyboardButton("🚫 Bloklash"), KeyboardButton("✅ Blokdan Chiqarish")],
        [KeyboardButton("📋 Bloklangan Ro’yxat"), KeyboardButton("📨 So’rovlar")],
        [KeyboardButton("👤 Admin Qo’shish"), KeyboardButton("🗑 Admin O’chirish")],
        [KeyboardButton("📋 Adminlar Ro’yxati")],
    ],
    resize_keyboard=True
)