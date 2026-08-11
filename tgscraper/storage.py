import sqlite3
from typing import Optional, List, Dict, Any


class MessageStore:
    def __init__(self, db_path: str = "tgscraper.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        # wal mode prevents reader locking issues when cli runs continuous loops
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                channel TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                text TEXT,
                views TEXT,
                has_media INTEGER DEFAULT 0,
                raw_html TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel, message_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_scraped ON messages (scraped_at DESC)"
        )
        self.conn.commit()

    def save_message(self, msg: Dict[str, Any]) -> bool:
        query = """
            INSERT OR IGNORE INTO messages (
                channel, message_id, datetime, text, views, has_media, raw_html
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cur = self.conn.cursor()
        cur.execute(
            query,
            (
                msg["channel"],
                msg["message_id"],
                msg["datetime"],
                msg.get("text", ""),
                msg.get("views"),
                1 if msg.get("has_media") else 0,
                msg.get("raw_html", ""),
            ),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def save_batch(self, messages: List[Dict[str, Any]]) -> int:
        if not messages:
            return 0
        query = """
            INSERT OR IGNORE INTO messages (
                channel, message_id, datetime, text, views, has_media, raw_html
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        rows = [
            (
                m["channel"],
                m["message_id"],
                m["datetime"],
                m.get("text", ""),
                m.get("views"),
                1 if m.get("has_media") else 0,
                m.get("raw_html", ""),
            )
            for m in messages
        ]
        cur = self.conn.cursor()
        cur.executemany(query, rows)
        self.conn.commit()
        return cur.rowcount

    def get_latest_id(self, channel: str) -> Optional[int]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT MAX(message_id) FROM messages WHERE channel = ?",
            (channel,),
        )
        row = cur.fetchone()
        if row and row[0] is not None:
            return row[0]
        return None

    def query_recent(self, channel: str, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT channel, message_id, datetime, text, views, has_media, scraped_at
            FROM messages
            WHERE channel = ?
            ORDER BY message_id DESC
            LIMIT ?
            """,
            (channel, limit),
        )
        return [dict(r) for r in cur.fetchall()]

    def search_text(self, pattern: str, limit: int = 20) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT channel, message_id, datetime, text, views
            FROM messages
            WHERE text LIKE ?
            ORDER BY message_id DESC
            LIMIT ?
            """,
            (f"%{pattern}%", limit),
        )
        return [dict(r) for r in cur.fetchall()]

    def close(self):
        self.conn.close()
