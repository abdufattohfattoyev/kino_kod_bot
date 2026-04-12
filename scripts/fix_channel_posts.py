"""
Kanalning barcha postlarida:
  - 2024 → 2026 (username va matnlarda)
  - Instagram haqidagi qatorlarni o'chirish

Ishlatish:
  cd ~/kino_kod_bot
  pip install pyrogram tgcrypto
  python scripts/fix_channel_posts.py

Kerakli ma'lumotlar:
  API_ID va API_HASH: https://my.telegram.org → App configuration
  CHANNEL: kanal username yoki ID (@KINO_MANIA_2024 yoki -1001234567890)
"""

import asyncio
import re
import os
import sys

try:
    from pyrogram import Client
    from pyrogram.errors import MessageNotModified, FloodWait
except ImportError:
    print("❌ Pyrogram o'rnatilmagan. Quyidagini bajaring:")
    print("   pip install pyrogram tgcrypto")
    sys.exit(1)

# ── Sozlamalar ────────────────────────────────────────────────────────────────

# .env dan token olish
def get_env(key):
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    with open(env_path) as f:
        for line in f:
            if line.startswith(key + '='):
                return line.split('=', 1)[1].strip()
    return None

# my.telegram.org dan oling:
API_ID   = 0        # ← O'zgartiring
API_HASH = ""       # ← O'zgartiring

CHANNEL  = "@KINO_MANIA_2026"   # ← Kanal username

# ── O'zgartirish qoidalari ────────────────────────────────────────────────────

def fix_text(text: str) -> str | None:
    """Matnni tuzatadi. O'zgarish bo'lmasa None qaytaradi."""
    if not text:
        return None

    original = text

    # 2024 → 2026 (faqat kino/kanal nomlarida emas, hamma joyda)
    text = re.sub(r'(?i)kino_mania_2024', 'KINO_MANIA_2026', text)
    text = re.sub(r'(?i)kino_mania_2024', 'Kino_mania_2026', text)
    text = text.replace('KINO_MANIA_2024', 'KINO_MANIA_2026')
    text = text.replace('Kino_mania_2024', 'Kino_mania_2026')
    text = text.replace('kino_mania_2024', 'kino_mania_2026')
    text = text.replace('Kino_Mania_2024', 'Kino_Mania_2026')
    # Qolgan 2024 larni ham o'zgartirish (ehtiyot bo'ling — sana bo'lsa ham o'zgaradi)
    text = text.replace('2024', '2026')

    # Instagram qatorlarini o'chirish
    lines = text.split('\n')
    lines = [l for l in lines if 'instagram' not in l.lower()]
    text = '\n'.join(lines)

    # Bo'sh qatorlarni tozalash (3+ bo'sh qator → 2)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    if text == original:
        return None  # O'zgarish yo'q
    return text


# ── Asosiy funksiya ───────────────────────────────────────────────────────────

async def main():
    if not API_ID or not API_HASH:
        print("❌ API_ID va API_HASH ni skriptda to'ldiring!")
        print("   https://my.telegram.org → API development tools")
        return

    print(f"👤 User account bilan kirilmoqda...")
    print(f"📢 Kanal: {CHANNEL}")
    print("─" * 40)

    # USER session (bot emas) — telefon raqam bilan kiradi
    app = Client(
        "fix_session",
        api_id=API_ID,
        api_hash=API_HASH,
        # bot_token EMAS — user account ishlatiladi
    )

    async with app:
        total = 0
        edited = 0
        skipped = 0
        errors = 0

        print("📥 Kanal postlari o'qilmoqda...")

        async for msg in app.get_chat_history(CHANNEL):
            total += 1

            text = msg.text or msg.caption
            new_text = fix_text(text)

            if new_text is None:
                skipped += 1
                if total % 100 == 0:
                    print(f"   {total} ta post ko'rildi...")
                continue

            # Tahrirlash
            try:
                if msg.text:
                    await app.edit_message_text(
                        CHANNEL, msg.id, new_text,
                        disable_web_page_preview=True
                    )
                elif msg.caption:
                    await app.edit_message_caption(
                        CHANNEL, msg.id, new_text
                    )
                edited += 1
                print(f"✅ Post #{msg.id} tahrirlandi")

            except MessageNotModified:
                skipped += 1
            except FloodWait as e:
                print(f"⏳ FloodWait {e.value}s, kutilmoqda...")
                await asyncio.sleep(e.value)
            except Exception as e:
                errors += 1
                print(f"❌ Post #{msg.id} da xatolik: {e}")

            await asyncio.sleep(0.3)

    print("\n" + "=" * 40)
    print(f"✅ Tahrirlandi:     {edited} ta")
    print(f"⏭  O'zgarish yo'q: {skipped} ta")
    print(f"❌ Xatolik:        {errors} ta")
    print(f"📊 Jami ko'rildi:  {total} ta")


if __name__ == "__main__":
    asyncio.run(main())
