"""
SQLite database layer.

Tables:
  - updates   : Stores all fetched & processed items (deduplication + search)
  - sent_urls : Tracks URLs already sent to Telegram (deduplification guard)
  - chat_ids  : Registered Telegram chat IDs to broadcast to
"""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path("data/bot.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_cursor() -> Generator[sqlite3.Cursor, None, None]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables and indexes on first run."""
    with db_cursor() as cur:
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS updates (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT    NOT NULL UNIQUE,
                title       TEXT    NOT NULL,
                source_name TEXT    NOT NULL,
                category    TEXT    NOT NULL,
                published   TEXT,
                fetched_at  TEXT    NOT NULL,
                summary     TEXT,
                tags        TEXT,
                sent        INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_updates_fetched
                ON updates (fetched_at DESC);

            CREATE INDEX IF NOT EXISTS idx_updates_sent
                ON updates (sent);

            CREATE INDEX IF NOT EXISTS idx_updates_tags
                ON updates (tags);

            CREATE TABLE IF NOT EXISTS chat_ids (
                chat_id   INTEGER PRIMARY KEY,
                joined_at TEXT    NOT NULL
            );
        """)
    logger.info("Database initialised at %s", DB_PATH)


# --------------------------------------------------------------------------- #
#  Updates                                                                     #
# --------------------------------------------------------------------------- #

def url_exists(url: str) -> bool:
    """Return True if this URL has already been stored."""
    with db_cursor() as cur:
        cur.execute("SELECT 1 FROM updates WHERE url = ?", (url,))
        return cur.fetchone() is not None


def insert_update(
    url: str,
    title: str,
    source_name: str,
    category: str,
    published: Optional[str],
    summary: Optional[str],
    tags: Optional[str],
) -> int:
    """Insert a new update; return the new row id."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    with db_cursor() as cur:
        cur.execute(
            """INSERT OR IGNORE INTO updates
               (url, title, source_name, category, published, fetched_at, summary, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (url, title, source_name, category, published, fetched_at, summary, tags),
        )
        return cur.lastrowid or 0


def mark_sent(url: str) -> None:
    with db_cursor() as cur:
        cur.execute("UPDATE updates SET sent = 1 WHERE url = ?", (url,))


def get_latest_updates(limit: int = 5) -> List[sqlite3.Row]:
    with db_cursor() as cur:
        cur.execute(
            """SELECT * FROM updates
               ORDER BY fetched_at DESC
               LIMIT ?""",
            (limit,),
        )
        return cur.fetchall()


def get_unsent_updates() -> List[sqlite3.Row]:
    with db_cursor() as cur:
        cur.execute(
            """SELECT * FROM updates
               WHERE sent = 0
               ORDER BY fetched_at ASC"""
        )
        return cur.fetchall()


def search_updates(keyword: str, limit: int = 10) -> List[sqlite3.Row]:
    pattern = f"%{keyword}%"
    with db_cursor() as cur:
        cur.execute(
            """SELECT * FROM updates
               WHERE title LIKE ?
                  OR summary LIKE ?
                  OR tags LIKE ?
               ORDER BY fetched_at DESC
               LIMIT ?""",
            (pattern, pattern, pattern, limit),
        )
        return cur.fetchall()


def filter_by_tag(tag: str, limit: int = 10) -> List[sqlite3.Row]:
    pattern = f"%{tag}%"
    with db_cursor() as cur:
        cur.execute(
            """SELECT * FROM updates
               WHERE tags LIKE ?
               ORDER BY fetched_at DESC
               LIMIT ?""",
            (pattern, limit),
        )
        return cur.fetchall()


def get_weekly_updates() -> List[sqlite3.Row]:
    """All updates from the past 7 days, ordered by fetched_at desc."""
    with db_cursor() as cur:
        cur.execute(
            """SELECT * FROM updates
               WHERE fetched_at >= datetime('now', '-7 days')
               ORDER BY fetched_at DESC"""
        )
        return cur.fetchall()


# --------------------------------------------------------------------------- #
#  Chat IDs                                                                    #
# --------------------------------------------------------------------------- #

def register_chat(chat_id: int) -> None:
    joined_at = datetime.now(timezone.utc).isoformat()
    with db_cursor() as cur:
        cur.execute(
            "INSERT OR IGNORE INTO chat_ids (chat_id, joined_at) VALUES (?, ?)",
            (chat_id, joined_at),
        )


def get_all_chats() -> List[int]:
    with db_cursor() as cur:
        cur.execute("SELECT chat_id FROM chat_ids")
        return [row["chat_id"] for row in cur.fetchall()]
