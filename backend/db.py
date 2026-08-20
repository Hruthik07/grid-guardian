import csv
import secrets
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "grid_guardian.db"
ASSETS_SEED_CSV = Path(__file__).resolve().parent.parent / "data" / "assets.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    criticality TEXT NOT NULL DEFAULT 'high',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
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

CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES organizations(id),
    target_type TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    target_name TEXT NOT NULL,
    hazard_source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    headline TEXT NOT NULL,
    severity TEXT NOT NULL,
    risk_score REAL NOT NULL,
    contribution REAL NOT NULL,
    detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notified INTEGER NOT NULL DEFAULT 0,
    UNIQUE(org_id, target_type, target_id, hazard_source, event_type, headline)
);
"""

CRITICALITY_WEIGHT = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.2}
DEMO_ORG_TOKEN = "demo-token"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        _seed_demo_org_if_empty(conn)


def _seed_demo_org_if_empty(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT id FROM organizations WHERE token = ?", (DEMO_ORG_TOKEN,)).fetchone()
    if row:
        return
    cur = conn.execute(
        "INSERT INTO organizations (name, email, token) VALUES (?, ?, ?)",
        ("Grid Guardian Demo Org", "demo@gridguardian.local", DEMO_ORG_TOKEN),
    )
    org_id = cur.lastrowid
    with open(ASSETS_SEED_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            conn.execute(
                "INSERT INTO assets (org_id, name, type, lat, lon, criticality) VALUES (?, ?, ?, ?, ?, ?)",
                (org_id, row["name"], row["type"], float(row["lat"]), float(row["lon"]), row["criticality"]),
            )


# --- organizations ---

def create_organization(name: str, email: str) -> dict:
    token = secrets.token_urlsafe(24)
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO organizations (name, email, token) VALUES (?, ?, ?)", (name, email, token)
        )
        return {"id": cur.lastrowid, "name": name, "email": email, "token": token}


def get_organization_by_token(token: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM organizations WHERE token = ?", (token,)).fetchone()
        return dict(row) if row else None


def list_organizations() -> list[dict]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM organizations").fetchall()]


# --- assets ---

def add_asset(org_id: int, name: str, type_: str, lat: float, lon: float, criticality: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO assets (org_id, name, type, lat, lon, criticality) VALUES (?, ?, ?, ?, ?, ?)",
            (org_id, name, type_, lat, lon, criticality),
        )
        return cur.lastrowid


def list_assets(org_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM assets WHERE org_id = ?", (org_id,)).fetchall()
        assets = [dict(r) for r in rows]
    for a in assets:
        a["asset_id"] = f"asset-{a['id']}"
        a["criticality_weight"] = CRITICALITY_WEIGHT.get(a["criticality"], 0.3)
    return assets


# --- subscribers ---

def add_subscriber(org_id: int, name: str, email: str, address: str, lat: float, lon: float,
                    criticality: str = "high", phone: str | None = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO subscribers (org_id, name, email, phone, address, lat, lon, criticality) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (org_id, name, email, phone, address, lat, lon, criticality),
        )
        return cur.lastrowid


def list_subscribers(org_id: int | None = None) -> list[dict]:
    with get_connection() as conn:
        if org_id is None:
            rows = conn.execute("SELECT * FROM subscribers").fetchall()
        else:
            rows = conn.execute("SELECT * FROM subscribers WHERE org_id = ?", (org_id,)).fetchall()
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


# --- incidents ---

def log_incident(org_id: int, target_type: str, target_id: int, target_name: str, hazard: dict,
                  risk_score: float, contribution: float, notified: bool) -> bool:
    """Returns True if a new incident row was inserted, False if it already existed (dedup)."""
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO incidents (org_id, target_type, target_id, target_name, hazard_source, "
                "event_type, headline, severity, risk_score, contribution, notified) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (org_id, target_type, target_id, target_name, hazard["source"], hazard["event_type"],
                 hazard["headline"], hazard["severity"], risk_score, contribution, int(notified)),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def list_incidents(org_id: int, limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM incidents WHERE org_id = ? ORDER BY detected_at DESC LIMIT ?",
            (org_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
