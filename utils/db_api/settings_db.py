import sqlite3
import logging

logger = logging.getLogger(__name__)


class SettingsDB:
    def __init__(self, path_to_db: str):
        self.path = path_to_db
        self._create_table()

    def _conn(self):
        return sqlite3.connect(self.path, check_same_thread=False)

    def _create_table(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS Settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    def get(self, key: str, default: str = None) -> str:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM Settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set(self, key: str, value: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO Settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value)
            )
            conn.commit()

    def get_bool(self, key: str, default: bool = False) -> bool:
        return self.get(key, "1" if default else "0") == "1"

    def set_bool(self, key: str, value: bool):
        self.set(key, "1" if value else "0")
