import sqlite3
import threading
import logging

logger = logging.getLogger(__name__)


class JoinRequestDB:
    def __init__(self, path_to_db: str):
        self.path = path_to_db
        self._lock = threading.Lock()
        self._create_table()

    def _connect(self):
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _create_table(self):
        with self._lock:
            conn = self._connect()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS join_requests (
                    user_id  INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, channel_id)
                )
            """)
            conn.commit()
            conn.close()

    def add(self, user_id: int, channel_id: int):
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO join_requests (user_id, channel_id) VALUES (?, ?)",
                    (user_id, channel_id)
                )
                conn.commit()
                logger.info(f"Join request saqlandi: user={user_id}, channel={channel_id}")
            except Exception as e:
                logger.error(f"join_request add xatolik: {e}")
            finally:
                conn.close()

    def remove(self, user_id: int, channel_id: int):
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "DELETE FROM join_requests WHERE user_id = ? AND channel_id = ?",
                    (user_id, channel_id)
                )
                conn.commit()
            except Exception as e:
                logger.error(f"join_request remove xatolik: {e}")
            finally:
                conn.close()

    def has_request(self, user_id: int, channel_id: int) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "SELECT 1 FROM join_requests WHERE user_id = ? AND channel_id = ?",
                    (user_id, channel_id)
                )
                return cur.fetchone() is not None
            except Exception as e:
                logger.error(f"join_request has_request xatolik: {e}")
                return False
            finally:
                conn.close()

    def get_channels(self, user_id: int) -> set:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "SELECT channel_id FROM join_requests WHERE user_id = ?",
                    (user_id,)
                )
                return {row[0] for row in cur.fetchall()}
            except Exception as e:
                logger.error(f"join_request get_channels xatolik: {e}")
                return set()
            finally:
                conn.close()

    def count_by_channel(self) -> list:
        """Har bir kanal uchun so'rovlar soni. [(channel_id, count), ...]"""
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "SELECT channel_id, COUNT(*) FROM join_requests GROUP BY channel_id"
                )
                return cur.fetchall()
            except Exception as e:
                logger.error(f"join_request count_by_channel xatolik: {e}")
                return []
            finally:
                conn.close()

    def total_count(self) -> int:
        """Jami so'rovlar soni."""
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute("SELECT COUNT(*) FROM join_requests")
                row = cur.fetchone()
                return row[0] if row else 0
            except Exception as e:
                logger.error(f"join_request total_count xatolik: {e}")
                return 0
            finally:
                conn.close()
