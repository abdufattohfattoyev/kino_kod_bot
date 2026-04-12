from aiogram import executor

import asyncio
from handlers.users.middleware import SubscriptionMiddleware
from handlers.users.inline_search import load_bot_username
from handlers.users.backup import auto_backup_loop
from loader import dp, user_db, kino_db
import middlewares, filters, handlers
from utils.notify_admins import on_startup_notify
from utils.set_bot_commands import set_default_commands
from data import config

dp.middleware.setup(SubscriptionMiddleware())


async def on_startup(dispatcher):
    await set_default_commands(dispatcher)

    try:
        user_db.create_table_users()
        user_db.add_is_admin_column()
        user_db.add_is_blocked_column()
        kino_db.create_table_kino()
    except Exception as err:
        print(err)

    # DB dagi adminlarni ADMINS ro'yxatiga yuklash (Docker restart uchun)
    try:
        db_admins = user_db.get_all_admins()
        for admin_id, _ in db_admins:
            if admin_id not in config.ADMINS:
                config.ADMINS.append(admin_id)
    except Exception as err:
        print(f"Adminlarni yuklashda xatolik: {err}")

    await load_bot_username()
    await on_startup_notify(dispatcher)
    asyncio.create_task(auto_backup_loop())


if __name__ == '__main__':
    executor.start_polling(
        dp,
        on_startup=on_startup,
        allowed_updates=[
            "message",
            "callback_query",
            "chat_join_request",
            "chat_member",
            "my_chat_member",
            "inline_query",
        ]
    )
