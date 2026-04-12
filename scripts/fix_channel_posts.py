"""
Kanalning barcha postlarida:
  - 2024 → 2026
  - Instagram qatorlarini o'chirish

Faqat Bot API ishlatadi — login shart emas.
Bot kanalda admin bo'lishi va "Xabarlarni tahrirlash" huquqi bo'lishi kerak.

Ishlatish:
  cd ~/kino_kod_bot
  python scripts/fix_channel_posts.py
"""

import time
import re
import os
import requests

# ── Sozlamalar ────────────────────────────────────────────────────────────────

def get_env(key):
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    with open(env_path) as f:
        for line in f:
            if line.strip().startswith(key + '='):
                return line.split('=', 1)[1].strip()
    return None

BOT_TOKEN = get_env('BOT_TOKEN')
ADMIN_ID  = int(get_env('ADMINS').split(',')[0])
CHANNEL   = "@KINO_MANIA_2026"
MAX_MSG_ID = 10000   # Kanalda nechta post bo'lsa shundan ko'p qilib qo'ying

BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── Matnni tuzatish ───────────────────────────────────────────────────────────

def fix_text(text: str):
    if not text:
        return None
    original = text

    text = text.replace('KINO_MANIA_2024', 'KINO_MANIA_2026')
    text = text.replace('Kino_mania_2024', 'Kino_mania_2026')
    text = text.replace('Kino_Mania_2024', 'Kino_Mania_2026')
    text = text.replace('kino_mania_2024', 'kino_mania_2026')
    text = text.replace('KINO_mania_2024', 'KINO_mania_2026')
    text = text.replace('2024', '2026')

    lines = [l for l in text.split('\n') if 'instagram' not in l.lower()]
    text = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()

    return None if text == original else text

# ── Bot API chaqiruvlari ───────────────────────────────────────────────────────

def forward_msg(msg_id):
    r = requests.post(f"{BASE}/forwardMessage", json={
        "chat_id": ADMIN_ID,
        "from_chat_id": CHANNEL,
        "message_id": msg_id
    }, timeout=10)
    return r.json()

def delete_msg(msg_id):
    requests.post(f"{BASE}/deleteMessage", json={
        "chat_id": ADMIN_ID,
        "message_id": msg_id
    }, timeout=10)

def edit_text(msg_id, text):
    return requests.post(f"{BASE}/editMessageText", json={
        "chat_id": CHANNEL,
        "message_id": msg_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }, timeout=10).json()

def edit_caption(msg_id, caption):
    return requests.post(f"{BASE}/editMessageCaption", json={
        "chat_id": CHANNEL,
        "message_id": msg_id,
        "caption": caption,
        "parse_mode": "HTML"
    }, timeout=10).json()

# ── Asosiy ───────────────────────────────────────────────────────────────────

def main():
    print(f"🤖 Bot: {BOT_TOKEN[:25]}...")
    print(f"📢 Kanal: {CHANNEL}")
    print(f"👤 Admin ID: {ADMIN_ID}")
    print(f"🔍 Tekshiriladigan postlar: 1 → {MAX_MSG_ID}")
    print("─" * 45)

    total   = 0
    edited  = 0
    skipped = 0
    errors  = 0

    for msg_id in range(1, MAX_MSG_ID + 1):
        try:
            # Postni admin DMga forward qilib o'qiymiz
            result = forward_msg(msg_id)

            if not result.get('ok'):
                # Post mavjud emas yoki forward bo'lmaydi — o'tkazib yuboramiz
                continue

            total += 1
            fwd = result['result']
            fwd_id = fwd['message_id']

            # Matni olamiz
            has_text    = 'text' in fwd
            has_caption = 'caption' in fwd
            raw_text    = fwd.get('text') or fwd.get('caption') or ''

            new_text = fix_text(raw_text)

            if new_text:
                # Asl postni tahrirlaymiz
                if has_text:
                    res = edit_text(msg_id, new_text)
                elif has_caption:
                    res = edit_caption(msg_id, new_text)
                else:
                    res = {'ok': False}

                if res.get('ok'):
                    edited += 1
                    print(f"✅ #{msg_id} tahrirlandi")
                else:
                    errors += 1
                    desc = res.get('description', '')
                    print(f"❌ #{msg_id} tahrirlash xatolik: {desc}")
            else:
                skipped += 1

            # Forward qilingan xabarni o'chiramiz
            delete_msg(fwd_id)

        except requests.exceptions.RequestException as e:
            print(f"⚠️  #{msg_id} tarmoq xatoligi: {e}")

        except Exception as e:
            errors += 1
            print(f"❌ #{msg_id}: {e}")

        # Telegram flood limitdan qochish
        time.sleep(0.4)

        if msg_id % 100 == 0:
            print(f"   ── {msg_id} ta tekshirildi (tahrirlandi: {edited}) ──")

    print("\n" + "=" * 45)
    print(f"✅ Tahrirlandi:        {edited} ta")
    print(f"⏭  O'zgarish kerak emas: {skipped} ta")
    print(f"❌ Xatolik:            {errors} ta")
    print(f"📊 Jami ko'rildi:     {total} ta")


if __name__ == "__main__":
    main()
