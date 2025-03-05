from .database import Database
from datetime import datetime, timedelta
import pytz  # Mahalliy vaqt uchun kutubxona


# UserDatabase foydalanuvchilarni bazaga saqlash uchun
class UserDatabase(Database):
    def create_table_users(self):
        sql = """
            CREATE TABLE IF NOT EXISTS Users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id BIGINT NOT NULL,
                username VARCHAR(255) NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_active DATETIME NULL,
                is_admin BOOLEAN NOT NULL DEFAULT 0
                );
        """
        self.execute(sql, commit=True)

    def add_user(self, telegram_id: int, username: str, created_at=None):
        sql = """
            INSERT INTO Users(telegram_id, username, created_at) VALUES(?, ?, ?)
        """
        if created_at is None:
            created_at = datetime.now().isoformat()

        self.execute(sql, parameters=(telegram_id, username, created_at), commit=True)

    def select_all_users(self):
        sql = """
            SELECT * FROM Users
        """
        return self.execute(sql, fetchall=True)

    def count_users(self):
        sql = """
            SELECT COUNT(*) FROM Users
        """
        return self.execute(sql, fetchone=True)[0]

    def select_user(self, telegram_id: int):
        sql = """
            SELECT * FROM Users WHERE telegram_id = ?
        """
        return self.execute(sql, parameters=(telegram_id,), fetchone=True)

    def count_daily_users(self):
        # Mahalliy vaqt zonasini olish
        local_tz = pytz.timezone("Asia/Tashkent")

        # Mahalliy bugungi kunning boshini aniqlash
        now = datetime.now(local_tz)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        sql = """
            SELECT COUNT(*) FROM Users
            WHERE created_at >= ? AND created_at < ?
        """
        return self.execute(sql, parameters=(today_start.isoformat(), tomorrow_start.isoformat()), fetchone=True)[0]

    def count_weekly_users(self):
        sql = """
            SELECT COUNT(*) FROM Users
            WHERE DATE(created_at) >= DATE('now', '-7 days')
        """
        return self.execute(sql, fetchone=True)[0]

    def count_monthly_users(self):
        sql = """
            SELECT COUNT(*) FROM Users
            WHERE DATE(created_at) >= DATE('now', '-1 month')
        """
        return self.execute(sql, fetchone=True)[0]

    def update_last_active(self, telegram_id: int):
        sql = """
            UPDATE Users
            SET last_active = ?
            WHERE telegram_id = ?
        """
        last_active = datetime.now().isoformat()
        self.execute(sql, parameters=(last_active, telegram_id), commit=True)

    def count_active_daily_users(self):
        sql = """
            SELECT COUNT(*) FROM Users
            WHERE DATE(last_active) = DATE('now')
        """
        return self.execute(sql, fetchone=True)[0]

    def count_active_weekly_users(self):
        sql = """
            SELECT COUNT(*) FROM Users
            WHERE DATE(last_active) >= DATE('now', '-7 days')
        """
        return self.execute(sql, fetchone=True)[0]

    def count_active_monthly_users(self):
        sql = """
            SELECT COUNT(*) FROM Users
            WHERE DATE(last_active) >= DATE('now', '-1 month')
        """
        return self.execute(sql, fetchone=True)[0]

    def check_if_admin(self, user_id: int):
        query = "SELECT is_admin FROM Users WHERE telegram_id = ?"
        result = self.execute(query, parameters=(user_id,), fetchone=True)
        return result and result['is_admin'] == 1
