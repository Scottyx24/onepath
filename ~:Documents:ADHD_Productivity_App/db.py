"""
db.py — SQLite database layer for ADHD Productivity App
"""
import sqlite3
import json
import datetime
from pathlib import Path

# Use /tmp on Streamlit Cloud (where the app dir is read-only),
# fall back to the app directory when running locally.
import os as _os
_local_db = Path(__file__).parent / "adhd_app.db"
try:
    _local_db.touch(exist_ok=True)
    DB_PATH = _local_db
except (OSError, PermissionError):
    DB_PATH = Path("/tmp") / "adhd_app.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            category TEXT DEFAULT 'general',
            due_date TEXT,
            energy_level TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            pomodoros_estimated INTEGER DEFAULT 1,
            pomodoros_done INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            google_event_id TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS subtasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            title TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '✅',
            created_at TEXT DEFAULT (date('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER,
            date TEXT,
            done INTEGER DEFAULT 0,
            UNIQUE(habit_id, date),
            FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            tags TEXT DEFAULT '[]',
            summary TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS note_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER,
            title TEXT,
            done INTEGER DEFAULT 0,
            FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS pomodoro_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            task_title TEXT,
            duration_minutes INTEGER,
            phase TEXT DEFAULT 'focus',
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS accountability_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT,
            virtual_partner TEXT,
            duration_minutes INTEGER,
            focus_minutes INTEGER DEFAULT 0,
            reflection TEXT,
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS eod_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            stars INTEGER,
            reflection TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS time_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            block_type TEXT DEFAULT 'deep_work',
            start_time TEXT,
            end_time TEXT,
            date TEXT,
            google_event_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()


# ── Settings ─────────────────────────────────────────────────────────────────

def get_setting(key, default=None):
    conn = get_db()
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?,?)", (key, str(value)))
    conn.commit()
    conn.close()


# ── Tasks ─────────────────────────────────────────────────────────────────────

def get_tasks(status=None, category=None, priority=None):
    conn = get_db()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"; params.append(status)
    if category:
        query += " AND category=?"; params.append(category)
    if priority:
        query += " AND priority=?"; params.append(priority)
    query += " ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def add_task(title, priority="medium", category="general", due_date=None,
             energy_level="medium", pomodoros_estimated=1):
    conn = get_db()
    c = conn.execute(
        "INSERT INTO tasks (title,priority,category,due_date,energy_level,pomodoros_estimated) VALUES (?,?,?,?,?,?)",
        (title, priority, category, due_date, energy_level, pomodoros_estimated),
    )
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    return task_id


def update_task_status(task_id, status):
    conn = get_db()
    completed_at = datetime.datetime.now().isoformat() if status == "done" else None
    conn.execute("UPDATE tasks SET status=?, completed_at=? WHERE id=?", (status, completed_at, task_id))
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


def get_subtasks(task_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM subtasks WHERE task_id=?", (task_id,)).fetchall()
    conn.close()
    return rows


def add_subtask(task_id, title):
    conn = get_db()
    conn.execute("INSERT INTO subtasks (task_id, title) VALUES (?,?)", (task_id, title))
    conn.commit()
    conn.close()


def toggle_subtask(subtask_id, done):
    conn = get_db()
    conn.execute("UPDATE subtasks SET done=? WHERE id=?", (1 if done else 0, subtask_id))
    conn.commit()
    conn.close()


def delete_subtask(subtask_id):
    conn = get_db()
    conn.execute("DELETE FROM subtasks WHERE id=?", (subtask_id,))
    conn.commit()
    conn.close()


# ── Habits ────────────────────────────────────────────────────────────────────

def get_habits():
    conn = get_db()
    rows = conn.execute("SELECT * FROM habits ORDER BY id").fetchall()
    conn.close()
    return rows


def add_habit(name, icon="✅"):
    conn = get_db()
    conn.execute("INSERT INTO habits (name, icon) VALUES (?,?)", (name, icon))
    conn.commit()
    conn.close()


def delete_habit(habit_id):
    conn = get_db()
    conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))
    conn.commit()
    conn.close()


def toggle_habit_today(habit_id, done):
    date = datetime.date.today().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO habit_logs (habit_id, date, done) VALUES (?,?,?)",
        (habit_id, date, 1 if done else 0),
    )
    conn.commit()
    conn.close()


def get_habit_done_today(habit_id):
    date = datetime.date.today().isoformat()
    conn = get_db()
    row = conn.execute(
        "SELECT done FROM habit_logs WHERE habit_id=? AND date=?", (habit_id, date)
    ).fetchone()
    conn.close()
    return bool(row and row["done"])


def get_habit_streak(habit_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT date FROM habit_logs WHERE habit_id=? AND done=1 ORDER BY date DESC", (habit_id,)
    ).fetchall()
    conn.close()
    if not rows:
        return 0
    dates = {r["date"] for r in rows}
    streak = 0
    check = datetime.date.today()
    while check.isoformat() in dates:
        streak += 1
        check -= datetime.timedelta(days=1)
    return streak


# ── Notes ─────────────────────────────────────────────────────────────────────

def save_note(content, tags=None, summary=None):
    conn = get_db()
    c = conn.execute(
        "INSERT INTO notes (content, tags, summary) VALUES (?,?,?)",
        (content, json.dumps(tags or []), summary),
    )
    note_id = c.lastrowid
    conn.commit()
    conn.close()
    return note_id


def get_notes():
    conn = get_db()
    rows = conn.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def update_note_analysis(note_id, tags, summary):
    conn = get_db()
    conn.execute(
        "UPDATE notes SET tags=?, summary=? WHERE id=?", (json.dumps(tags), summary, note_id)
    )
    conn.commit()
    conn.close()


def delete_note(note_id):
    conn = get_db()
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()
    conn.close()


def save_note_actions(note_id, action_items):
    """Save extracted action items and also add them as tasks."""
    conn = get_db()
    for item in action_items:
        conn.execute("INSERT INTO note_actions (note_id, title) VALUES (?,?)", (note_id, item))
        conn.execute("INSERT INTO tasks (title, category) VALUES (?,?)", (item, "from_note"))
    conn.commit()
    conn.close()


# ── Pomodoro ──────────────────────────────────────────────────────────────────

def log_pomodoro(task_id, task_title, duration_minutes, phase="focus"):
    now = datetime.datetime.now().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO pomodoro_sessions (task_id, task_title, duration_minutes, phase, started_at, completed_at) VALUES (?,?,?,?,?,?)",
        (task_id, task_title, duration_minutes, phase, now, now),
    )
    if task_id and phase == "focus":
        conn.execute("UPDATE tasks SET pomodoros_done = pomodoros_done + 1 WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


def get_pomodoro_sessions(limit=15):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM pomodoro_sessions ORDER BY completed_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows


def get_focus_minutes_by_day(days=7):
    conn = get_db()
    rows = conn.execute(
        """SELECT date(completed_at) as day, SUM(duration_minutes) as total
           FROM pomodoro_sessions WHERE phase='focus'
           AND completed_at >= date('now', ?)
           GROUP BY day ORDER BY day""",
        (f"-{days} days",),
    ).fetchall()
    conn.close()
    return {r["day"]: r["total"] for r in rows}


# ── EOD Reviews ───────────────────────────────────────────────────────────────

def save_eod_review(stars, reflection):
    today = datetime.date.today().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO eod_reviews (date, stars, reflection) VALUES (?,?,?)",
        (today, stars, reflection),
    )
    conn.commit()
    conn.close()


def get_today_eod():
    today = datetime.date.today().isoformat()
    conn = get_db()
    row = conn.execute("SELECT * FROM eod_reviews WHERE date=?", (today,)).fetchone()
    conn.close()
    return row


# ── Accountability ────────────────────────────────────────────────────────────

def save_accountability_session(goal, partner_name, duration, focus_min, reflection):
    now = datetime.datetime.now().isoformat()
    conn = get_db()
    conn.execute(
        """INSERT INTO accountability_sessions
           (goal, virtual_partner, duration_minutes, focus_minutes, reflection, completed_at)
           VALUES (?,?,?,?,?,?)""",
        (goal, partner_name, duration, focus_min, reflection, now),
    )
    conn.commit()
    conn.close()


def get_accountability_focus_by_day(days=7):
    conn = get_db()
    rows = conn.execute(
        """SELECT date(started_at) as day, SUM(focus_minutes) as total
           FROM accountability_sessions
           WHERE started_at >= date('now', ?)
           GROUP BY day ORDER BY day""",
        (f"-{days} days",),
    ).fetchall()
    conn.close()
    return {r["day"]: r["total"] for r in rows}


# ── Time Blocks ───────────────────────────────────────────────────────────────

def get_time_blocks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM time_blocks ORDER BY date, start_time").fetchall()
    conn.close()
    return rows


def add_time_block(title, block_type, start_time, end_time, date, google_event_id=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO time_blocks (title, block_type, start_time, end_time, date, google_event_id) VALUES (?,?,?,?,?,?)",
        (title, block_type, start_time, end_time, date, google_event_id),
    )
    conn.commit()
    conn.close()


def delete_time_block(block_id):
    conn = get_db()
    row = conn.execute("SELECT google_event_id FROM time_blocks WHERE id=?", (block_id,)).fetchone()
    conn.execute("DELETE FROM time_blocks WHERE id=?", (block_id,))
    conn.commit()
    conn.close()
    return row["google_event_id"] if row else None
