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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

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
MAX_MSG_ID  = 10000   # Kanalda nechta post bo'lsa shundan ko'p qilib qo'ying
WORKERS     = 3       # Parallel ishchi soni
FORWARD_DELAY = 0.8  # Forward orasidagi kutish (soniya) — FloodWait dan qochish uchun

BASE          = f"https://api.telegram.org/bot{BOT_TOKEN}"
_forward_lock = threading.Lock()   # Bir vaqtda faqat 1 ta forward

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
    with _forward_lock:
        time.sleep(FORWARD_DELAY)
        r = requests.post(f"{BASE}/forwardMessage", json={
            "chat_id": ADMIN_ID,
            "from_chat_id": CHANNEL,
            "message_id": msg_id
        }, timeout=10)
        data = r.json()
        # FloodWait bo'lsa kutamiz
        if not data.get('ok') and 'retry after' in data.get('description', '').lower():
            wait = int(re.search(r'\d+', data['description']).group()) + 2
            print(f"⏳ Forward FloodWait {wait}s...")
            time.sleep(wait)
            r = requests.post(f"{BASE}/forwardMessage", json={
                "chat_id": ADMIN_ID,
                "from_chat_id": CHANNEL,
                "message_id": msg_id
            }, timeout=10)
            data = r.json()
        return data

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

def process_one(msg_id):
    """Bitta postni tekshirib, kerak bo'lsa tahrirlaydi. (status, msg_id) qaytaradi."""
    try:
        result = forward_msg(msg_id)
        if not result.get('ok'):
            return ('skip', msg_id, '')

        fwd    = result['result']
        fwd_id = fwd['message_id']
        has_text    = 'text' in fwd
        has_caption = 'caption' in fwd
        raw_text    = fwd.get('text') or fwd.get('caption') or ''

        new_text = fix_text(raw_text)

        status = 'skip'
        desc   = ''
        if new_text:
            if has_text:
                res = edit_text(msg_id, new_text)
            elif has_caption:
                res = edit_caption(msg_id, new_text)
            else:
                res = {'ok': False}

            if res.get('ok'):
                status = 'edited'
            else:
                status = 'error'
                desc   = res.get('description', '')
                # FloodWait — biroz kutib qayta urinamiz
                if 'retry after' in desc.lower():
                    wait = int(re.search(r'\d+', desc).group()) + 1
                    time.sleep(wait)
                    res2 = edit_text(msg_id, new_text) if has_text else edit_caption(msg_id, new_text)
                    if res2.get('ok'):
                        status = 'edited'
                        desc   = ''

        delete_msg(fwd_id)
        return (status, msg_id, desc)

    except Exception as e:
        return ('error', msg_id, str(e))


def main():
    print(f"🤖 Bot: {BOT_TOKEN[:25]}...")
    print(f"📢 Kanal: {CHANNEL}")
    print(f"👤 Admin ID: {ADMIN_ID}")
    print(f"🔍 Postlar: 1 → {MAX_MSG_ID}  |  Parallel: {WORKERS} ta")
    print("─" * 45)

    total   = 0
    edited  = 0
    skipped = 0
    errors  = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(process_one, i): i for i in range(1, MAX_MSG_ID + 1)}

        for future in as_completed(futures):
            status, msg_id, desc = future.result()

            if status == 'skip':
                skipped += 1
            elif status == 'edited':
                total  += 1
                edited += 1
                print(f"✅ #{msg_id} tahrirlandi")
            elif status == 'error':
                total  += 1
                errors += 1
                if desc:
                    print(f"❌ #{msg_id}: {desc}")

            done = edited + errors + skipped
            if done % 200 == 0:
                print(f"   ── {done} ta tekshirildi (tahrirlandi: {edited}) ──")

    print("\n" + "=" * 45)
    print(f"✅ Tahrirlandi:           {edited} ta")
    print(f"⏭  O'zgarish kerak emas: {skipped} ta")
    print(f"❌ Xatolik:               {errors} ta")


if __name__ == "__main__":
    main()
