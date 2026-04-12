import logging

from aiogram import types

from loader import dp, kino_db, bot

logger = logging.getLogger(__name__)

# Bot username startup da yuklanadi (app.py da set qilinadi)
BOT_USERNAME = None


async def load_bot_username():
    global BOT_USERNAME
    me = await bot.get_me()
    BOT_USERNAME = me.username


@dp.inline_handler()
async def inline_search_handler(query: types.InlineQuery):
    search_text = query.query.strip()
    results = []

    try:
        if search_text:
            movies = kino_db.search_for_inline(search_text, limit=20)
        else:
            movies = kino_db.get_top_inline(limit=20)

        username = BOT_USERNAME or "bot"

        for movie in movies:
            post_id, file_id, caption = movie
            title = caption or f"Kino #{post_id}"
            deep_link = f"https://t.me/{username}?start={post_id}"

            import urllib.parse
            share_url = (
                f"https://t.me/share/url?"
                f"url={urllib.parse.quote(deep_link, safe='')}"
                f"&text={urllib.parse.quote('🎬 ' + title, safe='')}"
            )

            result = types.InlineQueryResultCachedVideo(
                id=str(post_id),
                video_file_id=file_id,
                title=title,
                caption=f"🎬 <b>{title}</b>\n\n"
                        f"👇 Kinoni ko'rish uchun tugmani bosing:",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(row_width=2).add(
                    types.InlineKeyboardButton("▶️ Kinoni ko'rish", url=deep_link),
                    types.InlineKeyboardButton("📤 Ulashish", url=share_url)
                )
            )
            results.append(result)

    except Exception as e:
        logger.error(f"Inline qidirishda xatolik: {e}")

    await query.answer(
        results,
        cache_time=5,
        is_personal=False
    )
