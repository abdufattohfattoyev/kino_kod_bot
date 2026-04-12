"""
Kanalning barcha postlarida 2024→2026 va Instagram qatorlarini o'chirish.
Ishlatish:
  cd ~/kino_kod_bot
  source venv/bin/activate
  python scripts/fix_channel_posts.py
"""

import time, re, os, requests

# ── Sozlamalar ────────────────────────────────────────────────────────────────

def get_env(key):
    with open(os.path.join(os.path.dirname(__file__), '..', '.env')) as f:
        for line in f:
            if line.strip().startswith(key + '='):
                return line.split('=', 1)[1].strip()

BOT_TOKEN = get_env('BOT_TOKEN')
ADMIN_ID  = int(get_env('ADMINS').split(',')[0])
CHANNEL   = "@KINO_MANIA_2026"
MAX_MSG_ID = 10000
BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── Matn tuzatish ─────────────────────────────────────────────────────────────

def fix_text(text):
    if not text:
        return None
    orig = text
    for old, new in [
        ('KINO_MANIA_2024','KINO_MANIA_2026'),
        ('Kino_mania_2024','Kino_mania_2026'),
        ('Kino_Mania_2024','Kino_Mania_2026'),
        ('kino_mania_2024','kino_mania_2026'),
    ]:
        text = text.replace(old, new)
    text = text.replace('2024', '2026')
    lines = [l for l in text.split('\n') if 'instagram' not in l.lower()]
    text = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()
    return None if text == orig else text

# ── API ───────────────────────────────────────────────────────────────────────

def api(method, **kwargs):
    """Avtomatik FloodWait bilan API chaqiruvi."""
    while True:
        r = requests.post(f"{BASE}/{method}", json=kwargs, timeout=15).json()
        if r.get('ok'):
            return r['result']
        desc = r.get('description', '')
        if 'retry after' in desc.lower():
            wait = int(re.search(r'\d+', desc).group()) + 1
            print(f"⏳ FloodWait {wait}s ({method})...")
            time.sleep(wait)
            continue
        return None  # boshqa xatolik — None

# ── Asosiy ───────────────────────────────────────────────────────────────────

def main():
    print(f"📢 Kanal: {CHANNEL}  |  Admin: {ADMIN_ID}")
    print(f"🔍 1 → {MAX_MSG_ID}")
    print("─" * 45)

    edited = errors = found = 0

    for msg_id in range(1, MAX_MSG_ID + 1):

        # Forward → matnni o'qiymiz
        fwd = api('forwardMessage', chat_id=ADMIN_ID,
                  from_chat_id=CHANNEL, message_id=msg_id)

        if fwd is None:
            continue  # Post yo'q — kutmasdan o'tkazamiz

        found += 1
        fwd_id   = fwd['message_id']
        has_text = 'text' in fwd
        raw      = fwd.get('text') or fwd.get('caption') or ''
        new_text = fix_text(raw)

        if new_text:
            method = 'editMessageText' if has_text else 'editMessageCaption'
            key    = 'text' if has_text else 'caption'
            res = api(method, chat_id=CHANNEL, message_id=msg_id,
                      **{key: new_text}, parse_mode='HTML',
                      disable_web_page_preview=True)
            if res:
                edited += 1
                print(f"✅ #{msg_id} tahrirlandi")
            else:
                errors += 1
                print(f"❌ #{msg_id} tahrirlashda xatolik")

        # Forward o'chiramiz
        api('deleteMessage', chat_id=ADMIN_ID, message_id=fwd_id)

        # Faqat mavjud postlarda kutamiz (1.1s = Telegram limiti)
        time.sleep(1.1)

        if found % 50 == 0:
            print(f"   ── {found} post ko'rildi, {edited} ta tahrirlandi ──")

    print("\n" + "=" * 45)
    print(f"✅ Tahrirlandi: {edited} ta")
    print(f"❌ Xatolik:     {errors} ta")
    print(f"📊 Topilgan:    {found} ta post")

if __name__ == "__main__":
    main()
