import sqlite3
import os
from datetime import datetime
from config import DB_PATH


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time_start TEXT NOT NULL,
            time_end TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(date);

        CREATE TABLE IF NOT EXISTS reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            summary TEXT NOT NULL,
            reflection TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS review_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            user_problem TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'in_progress',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS review_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES review_sessions(id)
        );
    ''')
    conn.close()


# --- Activities CRUD ---

def insert_activity(date, time_start, time_end, category, content):
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO activities (date, time_start, time_end, category, content, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        (date, time_start, time_end, category, content, datetime.now().isoformat())
    )
    activity_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return activity_id


def get_activities_by_date(date):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM activities WHERE date = ? ORDER BY time_start',
        (date,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_activities_by_range(date_from, date_to):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM activities WHERE date >= ? AND date <= ? ORDER BY date, time_start',
        (date_from, date_to)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_activity_by_id(activity_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM activities WHERE id = ?', (activity_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_activity(activity_id, date, time_start, time_end, category, content):
    conn = get_db()
    conn.execute(
        'UPDATE activities SET date=?, time_start=?, time_end=?, category=?, content=? WHERE id=?',
        (date, time_start, time_end, category, content, activity_id)
    )
    conn.commit()
    conn.close()


def delete_activity(activity_id):
    conn = get_db()
    conn.execute('DELETE FROM activities WHERE id = ?', (activity_id,))
    conn.commit()
    conn.close()


# --- Reflections ---

def save_reflection(date, summary, reflection):
    conn = get_db()
    conn.execute(
        'INSERT OR REPLACE INTO reflections (date, summary, reflection, created_at) VALUES (?, ?, ?, ?)',
        (date, summary, reflection, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_reflection(date):
    conn = get_db()
    row = conn.execute('SELECT * FROM reflections WHERE date = ?', (date,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Review Sessions ---

def create_review_session(date, user_problem):
    conn = get_db()
    # 若当天已有会话则更新，否则新建
    existing = conn.execute(
        'SELECT id FROM review_sessions WHERE date = ?', (date,)
    ).fetchone()
    if existing:
        conn.execute(
            'UPDATE review_sessions SET user_problem=?, status=?, created_at=? WHERE date=?',
            (user_problem, 'in_progress', datetime.now().isoformat(), date)
        )
        # 清空旧消息
        conn.execute('DELETE FROM review_messages WHERE session_id=?', (existing['id'],))
        session_id = existing['id']
    else:
        cursor = conn.execute(
            'INSERT INTO review_sessions (date, user_problem, status, created_at) VALUES (?, ?, ?, ?)',
            (date, user_problem, 'in_progress', datetime.now().isoformat())
        )
        session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def add_review_message(session_id, role, content):
    conn = get_db()
    conn.execute(
        'INSERT INTO review_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)',
        (session_id, role, content, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_review_session(date):
    conn = get_db()
    session = conn.execute(
        'SELECT * FROM review_sessions WHERE date = ?', (date,)
    ).fetchone()
    if not session:
        conn.close()
        return None
    session_dict = dict(session)
    messages = conn.execute(
        'SELECT role, content FROM review_messages WHERE session_id = ? ORDER BY created_at',
        (session_dict['id'],)
    ).fetchall()
    session_dict['messages'] = [dict(m) for m in messages]
    conn.close()
    return session_dict


def complete_review_session(session_id):
    conn = get_db()
    conn.execute(
        'UPDATE review_sessions SET status=? WHERE id=?',
        ('completed', session_id)
    )
    conn.commit()
    conn.close()


def get_all_review_sessions():
    conn = get_db()
    rows = conn.execute(
        'SELECT id, date, user_problem, status, created_at FROM review_sessions ORDER BY date DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
