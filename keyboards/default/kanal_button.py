from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

kanal_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🎲 Tasodifiy Kino"),
            KeyboardButton(text="🏆 Top 10 Kino"),
        ],
        [
            KeyboardButton(text="📽 Barcha kinolar"),
        ],
    ],
    resize_keyboard=True,
)
