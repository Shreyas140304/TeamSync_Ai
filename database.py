import sqlite3
from pathlib import Path
from logging_config import log_event

DB_PATH = Path("data/teamsync.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

import json


def save_meeting(title, meeting_date, participants, raw_notes, analysis):
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO meetings
                    (title, meeting_date, participants, raw_notes, summary, decisions)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    meeting_date,
                    participants,
                    raw_notes,
                    analysis.summary,
                    json.dumps(analysis.decisions),
                ),
            )

            meeting_id = cursor.lastrowid

            for item in analysis.action_items:
                conn.execute(
                    """
                    INSERT INTO action_items
                        (meeting_id, description, owner, due_date)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        meeting_id,
                        item.description,
                        item.owner,
                        item.due_date,
                    ),
                )

        log_event(
            "info",
            "meeting_created",
            meeting_id=meeting_id,
            action_items_count=len(analysis.action_items),
        )
        return meeting_id
    except Exception as exc:
        log_event(
            "error",
            "meeting_save_failed",
            error_type=type(exc).__name__,
        )
        raise
    
def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                meeting_date TEXT NOT NULL,
                participants TEXT,
                raw_notes TEXT NOT NULL,
                summary TEXT,
                decisions TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS action_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                owner TEXT,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'Open',
                outcome TEXT,
                carried_from INTEGER,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id),
                FOREIGN KEY (carried_from) REFERENCES action_items(id)
            )
        """)

def get_all_tasks():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                a.id,
                a.meeting_id,
                a.description,
                a.owner,
                a.due_date,
                a.status,
                a.outcome,
                m.title AS meeting_title
            FROM action_items a
            JOIN meetings m ON a.meeting_id = m.id
            ORDER BY a.id DESC
        """).fetchall()

        return [dict(row) for row in rows]


def update_task_status(task_id, status, outcome=None):
    allowed_statuses = {
    "Open",
    "In Progress",
    "Completed",
    "Carried Forward",
}

    if status not in allowed_statuses:
        raise ValueError("Invalid task status.")

    with get_connection() as conn:
        cursor = conn.execute("""
            UPDATE action_items
            SET status = ?, outcome = ?
            WHERE id = ?
        """, (status, outcome, task_id))

        if cursor.rowcount == 0:
            raise ValueError("Task not found.")

    log_event(
        "info",
        "task_status_updated",
        task_id=task_id,
        status=status,
    )


def update_task_owner(task_id, owner):
    normalized_owner = owner.strip() if owner and owner.strip() else None

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE action_items
            SET owner = ?
            WHERE id = ?
            """,
            (normalized_owner, task_id),
        )

        if cursor.rowcount == 0:
            raise ValueError("Task not found.")

    log_event(
        "info",
        "task_reassigned",
        task_id=task_id,
        owner=normalized_owner or "Unassigned",
    )


def get_open_tasks(owner=None):
    query = """
        SELECT
            a.id,
            a.description,
            a.owner,
            a.due_date,
            a.status,
            a.outcome,
            m.title AS meeting_title,
            m.meeting_date
        FROM action_items a
        JOIN meetings m ON a.meeting_id = m.id
        WHERE a.status IN ('Open', 'In Progress')
    """

    params = []

    if owner:
        query += " AND LOWER(TRIM(a.owner)) = LOWER(TRIM(?))"
        params.append(owner.strip())

    query += " ORDER BY a.due_date IS NULL, a.due_date ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

def carry_forward_task(task_id, new_meeting_id):
    with get_connection() as conn:

        # Find the original task
        task = conn.execute(
            """
            SELECT *
            FROM action_items
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()

        if task is None:
            raise ValueError("Task not found.")

        if task["status"] in ("Completed", "Carried Forward"):
            raise ValueError(
                "Only unfinished tasks can be carried forward."
            )

        # Check that the destination meeting exists
        meeting = conn.execute(
            "SELECT id FROM meetings WHERE id = ?",
            (new_meeting_id,),
        ).fetchone()

        if meeting is None:
            raise ValueError("Destination meeting not found.")

        # Create a new task linked to the original
        cursor = conn.execute(
            """
            INSERT INTO action_items
                (meeting_id, description, owner, due_date,
                 status, outcome, carried_from)
            VALUES (?, ?, ?, ?, 'Open', NULL, ?)
            """,
            (
                new_meeting_id,
                task["description"],
                task["owner"],
                task["due_date"],
                task_id,
            ),
        )

        new_task_id = cursor.lastrowid

        # Preserve the original, marking its lifecycle transition
        conn.execute(
            """
            UPDATE action_items
            SET status = 'Carried Forward'
            WHERE id = ?
            """,
            (task_id,),
        )
    log_event(
    "info",
    "task_carried_forward",
    old_task_id=task_id,
    new_task_id=new_task_id,
    destination_meeting_id=new_meeting_id,
)
    return new_task_id
    
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")