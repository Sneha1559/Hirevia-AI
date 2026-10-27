
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "hirevia.db"


def get_connection():
    """Create a SQLite connection with row-based access."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create tables and safely migrate existing databases."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                threshold INTEGER NOT NULL DEFAULT 60,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS screening_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                job_title TEXT NOT NULL,
                threshold INTEGER NOT NULL,
                report TEXT,
                processed_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            );

            CREATE TABLE IF NOT EXISTS candidate_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                rank INTEGER,
                candidate_name TEXT NOT NULL,
                score REAL,
                recommendation TEXT,
                matched_skills TEXT,
                missing_skills TEXT,
                strengths TEXT,
                concerns TEXT,
                explanation TEXT,
                FOREIGN KEY (session_id)
                    REFERENCES screening_sessions(id)
                    ON DELETE CASCADE
            );
            """
        )

        # Add new columns to older databases without deleting records.
        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(jobs)"
            ).fetchall()
        }

        migrations = {
            "company": "TEXT NOT NULL DEFAULT ''",
            "required_skills": "TEXT NOT NULL DEFAULT '[]'",
            "preferred_skills": "TEXT NOT NULL DEFAULT '[]'",
            "minimum_experience": "INTEGER NOT NULL DEFAULT 0",
        }

        for column, definition in migrations.items():
            if column not in existing_columns:
                connection.execute(
                    f"ALTER TABLE jobs ADD COLUMN {column} {definition}"
                )


def _decode_job(row):
    """Convert a database row to a job dictionary."""
    if row is None:
        return None

    job = dict(row)

    for field in ("required_skills", "preferred_skills"):
        try:
            job[field] = json.loads(job.get(field) or "[]")
        except (json.JSONDecodeError, TypeError):
            job[field] = []

    job["company"] = job.get("company") or ""
    job["minimum_experience"] = int(
        job.get("minimum_experience") or 0
    )
    return job


def save_job(
    title,
    description,
    threshold=60,
    company="",
    required_skills=None,
    preferred_skills=None,
    minimum_experience=0,
):
    """Save a job and return its database ID."""
    if not title or not title.strip():
        raise ValueError("Job title is required.")

    if not description or not description.strip():
        raise ValueError("Job description is required.")

    threshold = int(threshold)
    minimum_experience = int(minimum_experience)

    if not 0 <= threshold <= 100:
        raise ValueError("Threshold must be between 0 and 100.")

    if minimum_experience < 0:
        raise ValueError("Minimum experience cannot be negative.")

    required_skills = required_skills or []
    preferred_skills = preferred_skills or []

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO jobs (
                title, description, threshold, created_at,
                company, required_skills, preferred_skills,
                minimum_experience
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title.strip(),
                description.strip(),
                threshold,
                datetime.now().isoformat(timespec="seconds"),
                (company or "").strip(),
                json.dumps(required_skills),
                json.dumps(preferred_skills),
                minimum_experience,
            ),
        )
        return cursor.lastrowid


def get_jobs():
    """Return all saved jobs, newest first."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM jobs ORDER BY id DESC"
        ).fetchall()
        return [_decode_job(row) for row in rows]


def get_job(job_id):
    """Return one saved job, or None if not found."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        return _decode_job(row)


def update_job(
    job_id,
    title,
    description,
    threshold=60,
    company="",
    required_skills=None,
    preferred_skills=None,
    minimum_experience=0,
):
    """Update a saved job. Return True if it exists."""
    if not title or not title.strip():
        raise ValueError("Job title is required.")

    if not description or not description.strip():
        raise ValueError("Job description is required.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE jobs
            SET title = ?,
                description = ?,
                threshold = ?,
                company = ?,
                required_skills = ?,
                preferred_skills = ?,
                minimum_experience = ?
            WHERE id = ?
            """,
            (
                title.strip(),
                description.strip(),
                int(threshold),
                (company or "").strip(),
                json.dumps(required_skills or []),
                json.dumps(preferred_skills or []),
                int(minimum_experience),
                int(job_id),
            ),
        )
        return cursor.rowcount > 0


def delete_job(job_id):
    """
    Delete a saved job while preserving its screening history.
    Existing sessions are detached from the job before deletion.
    """
    with get_connection() as connection:
        exists = connection.execute(
            "SELECT id FROM jobs WHERE id = ?",
            (int(job_id),),
        ).fetchone()

        if not exists:
            return False

        connection.execute(
            """
            UPDATE screening_sessions
            SET job_id = NULL
            WHERE job_id = ?
            """,
            (int(job_id),),
        )

        connection.execute(
            "DELETE FROM jobs WHERE id = ?",
            (int(job_id),),
        )
        return True


def save_screening(screening, job_id=None):
    """Save a screening session and its structured candidate results."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO screening_sessions (
                job_id, job_title, threshold, report,
                processed_count, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                screening.get("job_title", "Untitled Job"),
                int(screening.get("threshold", 60)),
                screening.get("report", ""),
                int(screening.get("processed_count", 0)),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )

        session_id = cursor.lastrowid

        for candidate in screening.get("results", []):
            connection.execute(
                """
                INSERT INTO candidate_results (
                    session_id, rank, candidate_name, score,
                    recommendation, matched_skills, missing_skills,
                    strengths, concerns, explanation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    candidate.get("rank"),
                    candidate.get("candidate_name", "Unknown"),
                    candidate.get("score"),
                    candidate.get("recommendation", ""),
                    json.dumps(candidate.get("matched_skills", [])),
                    json.dumps(candidate.get("missing_skills", [])),
                    json.dumps(candidate.get("strengths", [])),
                    json.dumps(candidate.get("concerns", [])),
                    candidate.get("explanation", ""),
                ),
            )

        return session_id


def get_screening_history(limit=50):
    """Return recent screening sessions."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, job_id, job_title, threshold,
                   processed_count, created_at
            FROM screening_sessions
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()
        return [dict(row) for row in rows]


def get_screening_details(session_id):
    """Return one screening session with its candidate results."""
    with get_connection() as connection:
        session = connection.execute(
            "SELECT * FROM screening_sessions WHERE id = ?",
            (int(session_id),),
        ).fetchone()

        if not session:
            return None

        candidates = connection.execute(
            """
            SELECT * FROM candidate_results
            WHERE session_id = ?
            ORDER BY rank ASC, id ASC
            """,
            (int(session_id),),
        ).fetchall()

        result = dict(session)
        result["candidates"] = []

        for row in candidates:
            candidate = dict(row)

            for field in (
                "matched_skills",
                "missing_skills",
                "strengths",
                "concerns",
            ):
                try:
                    candidate[field] = json.loads(
                        candidate[field] or "[]"
                    )
                except (json.JSONDecodeError, TypeError):
                    candidate[field] = []

            result["candidates"].append(candidate)

        return result


# Ensure tables and migrations are ready when this module is imported.
initialize_database()
