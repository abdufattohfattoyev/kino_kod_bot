import sqlite3

conn = sqlite3.connect('data/kino.db')
cur = conn.cursor()

cur.execute('SELECT post_id, caption FROM Kino WHERE caption LIKE "%2024%"')
rows = cur.fetchall()
print(f'Topildi: {len(rows)} ta kino')

updated = 0
for post_id, caption in rows:
    if not caption:
        continue
    new = caption.replace('KINO_MANIA_2024', 'KINO_MANIA_2026')
    new = new.replace('Kino_mania_2024', 'Kino_mania_2026')
    new = new.replace('Kino_Mania_2024', 'Kino_Mania_2026')
    new = new.replace('kino_mania_2024', 'kino_mania_2026')
    new = new.replace('2024', '2026')
    cur.execute('UPDATE Kino SET caption=? WHERE post_id=?', (new, post_id))
    updated += 1

conn.commit()
conn.close()
print(f'Yangilandi: {updated} ta kino')
