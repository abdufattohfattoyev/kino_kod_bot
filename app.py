from aiogram import executor

from handlers.users.middleware import SubscriptionMiddleware
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

    await on_startup_notify(dispatcher)


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
        ]
    )
