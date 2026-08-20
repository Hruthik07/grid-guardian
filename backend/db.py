import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "grid_guardian.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    address TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    criticality TEXT NOT NULL DEFAULT 'high',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications_sent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscriber_id INTEGER NOT NULL,
    hazard_key TEXT NOT NULL,
    sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subscriber_id, hazard_key)
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def add_subscriber(name: str, email: str, address: str, lat: float, lon: float, criticality: str = "high") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO subscribers (name, email, address, lat, lon, criticality) VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, address, lat, lon, criticality),
        )
        return cur.lastrowid


def list_subscribers() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM subscribers").fetchall()
        return [dict(r) for r in rows]


def has_been_notified(subscriber_id: int, hazard_key: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM notifications_sent WHERE subscriber_id = ? AND hazard_key = ?",
            (subscriber_id, hazard_key),
        ).fetchone()
        return row is not None


def mark_notified(subscriber_id: int, hazard_key: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO notifications_sent (subscriber_id, hazard_key) VALUES (?, ?)",
            (subscriber_id, hazard_key),
        )
