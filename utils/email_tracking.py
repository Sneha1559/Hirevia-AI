
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "hirevia_email_tracking.db"


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_email_tracking():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS candidate_email_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                candidate_name TEXT NOT NULL,
                email TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                sent_at TEXT,
                error_message TEXT,
                UNIQUE(session_id, candidate_name, email)
            )
        """)


def get_email_status(session_id, candidate_name, email):
    with connect() as conn:
        row = conn.execute("""
            SELECT status, sent_at, error_message
            FROM candidate_email_status
            WHERE session_id = ? AND candidate_name = ? AND email = ?
        """, (str(session_id), candidate_name, email)).fetchone()
        return dict(row) if row else None


def save_email_status(session_id, candidate_name, email, status, error=""):
    sent_at = datetime.now().isoformat(timespec="seconds") if status == "Sent" else None

    with connect() as conn:
        conn.execute("""
            INSERT INTO candidate_email_status
                (session_id, candidate_name, email, status, sent_at, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, candidate_name, email)
            DO UPDATE SET
                status = excluded.status,
                sent_at = excluded.sent_at,
                error_message = excluded.error_message
        """, (
            str(session_id), candidate_name, email,
            status, sent_at, error or None
        ))
