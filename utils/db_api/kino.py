from .database import Database
from datetime import datetime

# Kinolarni saqlash uchun KinoDatabase klassi
class KinoDatabase(Database):
    def create_table_kino(self):
        sql = """
                CREATE TABLE IF NOT EXISTS Kino(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id BIGINT NOT NULL UNIQUE,
                    file_id VARCHAR(2000) NOT NULL,
                    caption TEXT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    count_download INTEGER NOT NULL DEFAULT 0,
                    updated_at DATETIME
                );
              """
        self.execute(sql, commit=True)
        # Ko'p qismli kinolar jadvali
        self.execute("""
            CREATE TABLE IF NOT EXISTS KinoParts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id BIGINT NOT NULL,
                part_number INTEGER NOT NULL,
                file_id VARCHAR(2000) NOT NULL,
                UNIQUE(post_id, part_number)
            );
        """, commit=True)

    def add_kino(self, post_id: int, file_id: str, caption: str):
        # Bazada kino mavjudligini tekshirish
        existing_kino = self.search_kino_by_post_id(post_id)
        if existing_kino:
            raise ValueError("Bu kod bilan kino allaqachon mavjud.")

        sql = """
            INSERT INTO Kino(post_id, file_id, caption, created_at, updated_at)
            VALUES(?,?,?,?,?)
        """
        timestamp = datetime.now().isoformat()
        self.execute(sql, parameters=(post_id, file_id, caption, timestamp, timestamp), commit=True)

    def delete_kino(self, post_id: int):
        sql = "DELETE FROM Kino WHERE post_id=?"
        self.execute(sql, parameters=(post_id,), commit=True)

    def search_kino_by_post_id(self, post_id: int):
        sql = "SELECT file_id, caption, count_download FROM Kino WHERE post_id=?"
        result = self.execute(sql, parameters=(post_id,), fetchone=True)
        if result:
            return {"file_id": result[0], "caption": result[1], "count_download": result[2]}
        return None

    def count_kinos(self):
        sql = "SELECT COUNT(*) FROM Kino"
        result = self.execute(sql, fetchone=True)
        return {"Jami Kinolar": result[0] if result else 0}

    def search_kino_by_caption(self, caption: str):
        sql = "SELECT file_id, caption FROM Kino WHERE caption LIKE ?"
        return self.execute(sql, (f"%{caption}%",), fetchall=True)

    def update_caption(self, post_id: int, new_caption: str):
        """Kino sarlavhasini yangilash."""
        sql = "UPDATE Kino SET caption = ?, updated_at = ? WHERE post_id = ?"
        from datetime import datetime
        self.execute(sql, parameters=(new_caption, datetime.now().isoformat(), post_id), commit=True)

    def update_file_id(self, post_id: int, new_file_id: str):
        """Kino asosiy faylini yangilash."""
        sql = "UPDATE Kino SET file_id = ?, updated_at = ? WHERE post_id = ?"
        from datetime import datetime
        self.execute(sql, parameters=(new_file_id, datetime.now().isoformat(), post_id), commit=True)

    def update_download_count(self, post_id: int):
        sql = "UPDATE Kino SET count_download = count_download + 1 WHERE post_id = ?"
        self.execute(sql, parameters=(post_id,), commit=True)

    def get_download_count(self, post_id: int):
        sql = "SELECT count_download FROM Kino WHERE post_id = ?"
        result = self.execute(sql, parameters=(post_id,), fetchone=True)
        return result[0] if result else 0

    # ── Ko'p qismli kinolar ───────────────────────────────────────────────

    def add_parts(self, post_id: int, file_ids: list):
        """Kinoning barcha qismlarini saqlash (yangi kino uchun, 1 dan boshlanadi)."""
        for i, file_id in enumerate(file_ids, start=1):
            self.execute(
                "INSERT OR IGNORE INTO KinoParts(post_id, part_number, file_id) VALUES(?,?,?)",
                parameters=(post_id, i, file_id), commit=True
            )

    def add_next_part(self, post_id: int, file_id: str) -> int:
        """Mavjud kinoga keyingi qismni qo'shadi. Yangi qism raqamini qaytaradi."""
        result = self.execute(
            "SELECT COALESCE(MAX(part_number), 0) FROM KinoParts WHERE post_id=?",
            parameters=(post_id,), fetchone=True
        )
        next_num = (result[0] if result else 0) + 1
        self.execute(
            "INSERT OR IGNORE INTO KinoParts(post_id, part_number, file_id) VALUES(?,?,?)",
            parameters=(post_id, next_num, file_id), commit=True
        )
        return next_num

    def get_parts(self, post_id: int) -> list:
        """Kinoning barcha qismlarini tartib bilan olish. [(part_number, file_id), ...]"""
        result = self.execute(
            "SELECT part_number, file_id FROM KinoParts WHERE post_id=? ORDER BY part_number",
            parameters=(post_id,), fetchall=True
        )
        return result or []

    def delete_parts(self, post_id: int):
        """Kinoning barcha qismlarini o'chirish."""
        self.execute(
            "DELETE FROM KinoParts WHERE post_id=?",
            parameters=(post_id,), commit=True
        )

    def count_parts(self, post_id: int) -> int:
        """Kino nechta qismdan iboratligini qaytaradi."""
        result = self.execute(
            "SELECT COUNT(*) FROM KinoParts WHERE post_id=?",
            parameters=(post_id,), fetchone=True
        )
        return result[0] if result else 0

    # ─────────────────────────────────────────────────────────────────────

    def get_random_kino(self):
        """Tasodifiy bir kinoni qaytaradi. (post_id, file_id, caption, count_download)"""
        sql = "SELECT post_id, file_id, caption, count_download FROM Kino ORDER BY RANDOM() LIMIT 1"
        result = self.execute(sql, fetchone=True)
        if result:
            return {"post_id": result[0], "file_id": result[1], "caption": result[2], "count_download": result[3]}
        return None

    def get_top_kinos(self, limit: int = 10):
        """Eng ko'p yuklab olingan kinolar. [(post_id, caption, count_download), ...]"""
        sql = """
            SELECT post_id, caption, count_download
            FROM Kino
            ORDER BY count_download DESC
            LIMIT ?
        """
        return self.execute(sql, parameters=(limit,), fetchall=True) or []

    def search_for_inline(self, query: str, limit: int = 20):
        """Inline qidirish uchun. [(post_id, file_id, caption), ...]"""
        sql = """
            SELECT post_id, file_id, caption
            FROM Kino
            WHERE caption LIKE ?
            ORDER BY count_download DESC
            LIMIT ?
        """
        return self.execute(sql, parameters=(f"%{query}%", limit), fetchall=True) or []

    def get_top_inline(self, limit: int = 20):
        """Eng mashhur kinolar inline uchun (query bo'sh bo'lsa). [(post_id, file_id, caption), ...]"""
        sql = """
            SELECT post_id, file_id, caption
            FROM Kino
            ORDER BY count_download DESC
            LIMIT ?
        """
        return self.execute(sql, parameters=(limit,), fetchall=True) or []

    def search_by_caption(self, query: str, limit: int = 8):
        """Kino nomi bo'yicha qidirish. [(post_id, caption, count_download), ...]"""
        sql = """
            SELECT post_id, caption, count_download
            FROM Kino
            WHERE caption LIKE ?
            ORDER BY count_download DESC
            LIMIT ?
        """
        return self.execute(sql, parameters=(f"%{query}%", limit), fetchall=True) or []
