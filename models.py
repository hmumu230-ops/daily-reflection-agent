import os
from datetime import datetime
from config import DATABASE_URL, DB_PATH

# 根据 DATABASE_URL 判断使用 PostgreSQL 还是 SQLite
USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3


def get_db():
    if USE_PG:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    else:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        return conn


def _execute(conn, sql, params=()):
    """统一执行 SQL，处理 PG 和 SQLite 的参数差异"""
    if USE_PG:
        # SQLite 用 ?，PostgreSQL 用 %s
        sql = sql.replace('?', '%s')
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def _fetchall(conn, sql, params=()):
    cur = _execute(conn, sql, params)
    rows = cur.fetchall()
    cur.close()
    if USE_PG:
        return rows  # already dicts
    return [dict(r) for r in rows]


def _fetchone(conn, sql, params=()):
    cur = _execute(conn, sql, params)
    row = cur.fetchone()
    cur.close()
    if USE_PG:
        return row  # already dict or None
    return dict(row) if row else None


def init_db():
    conn = get_db()
    if USE_PG:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                date TEXT NOT NULL,
                time_start TEXT NOT NULL,
                time_end TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(user_id, date)')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS reflections (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                date TEXT NOT NULL,
                summary TEXT NOT NULL,
                reflection TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, date)
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS review_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                date TEXT NOT NULL,
                user_problem TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'in_progress',
                created_at TEXT NOT NULL,
                UNIQUE(user_id, date)
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS review_messages (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES review_sessions(id),
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS note_summaries (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                date TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, date)
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                github_token TEXT,
                updated_at TEXT NOT NULL
            )
        ''')
        cur.close()
        conn.commit()
    else:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time_start TEXT NOT NULL,
                time_end TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(user_id, date);
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                summary TEXT NOT NULL,
                reflection TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, date)
            );
            CREATE TABLE IF NOT EXISTS review_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                user_problem TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'in_progress',
                created_at TEXT NOT NULL,
                UNIQUE(user_id, date)
            );
            CREATE TABLE IF NOT EXISTS review_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS note_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, date)
            );
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                github_token TEXT,
                updated_at TEXT NOT NULL
            );
        ''')
    conn.close()


# --- Users ---

def create_user(username, password_hash):
    conn = get_db()
    cur = _execute(conn, 'INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)',
                   (username, password_hash, datetime.now().isoformat()))
    if USE_PG:
        cur.execute('SELECT lastval()')
        user_id = cur.fetchone()['lastval']
    else:
        user_id = cur.lastrowid
    cur.close()
    conn.commit()
    conn.close()
    return user_id


def get_user_by_username(username):
    conn = get_db()
    row = _fetchone(conn, 'SELECT * FROM users WHERE username = ?', (username,))
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_db()
    row = _fetchone(conn, 'SELECT * FROM users WHERE id = ?', (user_id,))
    conn.close()
    return row


# --- Activities CRUD ---

def insert_activity(user_id, date, time_start, time_end, category, content):
    conn = get_db()
    cur = _execute(conn,
        'INSERT INTO activities (user_id, date, time_start, time_end, category, content, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (user_id, date, time_start, time_end, category, content, datetime.now().isoformat()))
    if USE_PG:
        cur.execute('SELECT lastval()')
        activity_id = cur.fetchone()['lastval']
    else:
        activity_id = cur.lastrowid
    cur.close()
    conn.commit()
    conn.close()
    return activity_id


def get_activities_by_date(user_id, date):
    conn = get_db()
    rows = _fetchall(conn,
        'SELECT * FROM activities WHERE user_id = ? AND date = ? ORDER BY time_start',
        (user_id, date))
    conn.close()
    return rows


def get_activities_by_range(user_id, date_from, date_to):
    conn = get_db()
    rows = _fetchall(conn,
        'SELECT * FROM activities WHERE user_id = ? AND date >= ? AND date <= ? ORDER BY date, time_start',
        (user_id, date_from, date_to))
    conn.close()
    return rows


def get_activity_by_id(user_id, activity_id):
    conn = get_db()
    row = _fetchone(conn, 'SELECT * FROM activities WHERE id = ? AND user_id = ?', (activity_id, user_id))
    conn.close()
    return row


def update_activity(user_id, activity_id, date, time_start, time_end, category, content):
    conn = get_db()
    _execute(conn,
        'UPDATE activities SET date=?, time_start=?, time_end=?, category=?, content=? WHERE id=? AND user_id=?',
        (date, time_start, time_end, category, content, activity_id, user_id))
    conn.commit()
    conn.close()


def delete_activity(user_id, activity_id):
    conn = get_db()
    _execute(conn, 'DELETE FROM activities WHERE id = ? AND user_id = ?', (activity_id, user_id))
    conn.commit()
    conn.close()


# --- Reflections ---

def save_reflection(user_id, date, summary, reflection):
    conn = get_db()
    if USE_PG:
        _execute(conn,
            '''INSERT INTO reflections (user_id, date, summary, reflection, created_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (user_id, date) DO UPDATE SET summary=EXCLUDED.summary, reflection=EXCLUDED.reflection, created_at=EXCLUDED.created_at''',
            (user_id, date, summary, reflection, datetime.now().isoformat()))
    else:
        _execute(conn,
            'INSERT OR REPLACE INTO reflections (user_id, date, summary, reflection, created_at) VALUES (?, ?, ?, ?, ?)',
            (user_id, date, summary, reflection, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_reflection(user_id, date):
    conn = get_db()
    row = _fetchone(conn, 'SELECT * FROM reflections WHERE user_id = ? AND date = ?', (user_id, date))
    conn.close()
    return row


# --- Review Sessions ---

def create_review_session(user_id, date, user_problem):
    conn = get_db()
    existing = _fetchone(conn, 'SELECT id FROM review_sessions WHERE user_id = ? AND date = ?', (user_id, date))
    if existing:
        _execute(conn,
            'UPDATE review_sessions SET user_problem=?, status=?, created_at=? WHERE user_id=? AND date=?',
            (user_problem, 'in_progress', datetime.now().isoformat(), user_id, date))
        _execute(conn, 'DELETE FROM review_messages WHERE session_id=?', (existing['id'],))
        session_id = existing['id']
    else:
        cur = _execute(conn,
            'INSERT INTO review_sessions (user_id, date, user_problem, status, created_at) VALUES (?, ?, ?, ?, ?)',
            (user_id, date, user_problem, 'in_progress', datetime.now().isoformat()))
        if USE_PG:
            cur.execute('SELECT lastval()')
            session_id = cur.fetchone()['lastval']
        else:
            session_id = cur.lastrowid
        cur.close()
    conn.commit()
    conn.close()
    return session_id


def add_review_message(session_id, role, content):
    conn = get_db()
    _execute(conn,
        'INSERT INTO review_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)',
        (session_id, role, content, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_review_session(user_id, date):
    conn = get_db()
    session = _fetchone(conn, 'SELECT * FROM review_sessions WHERE user_id = ? AND date = ?', (user_id, date))
    if not session:
        conn.close()
        return None
    messages = _fetchall(conn,
        'SELECT role, content FROM review_messages WHERE session_id = ? ORDER BY created_at',
        (session['id'],))
    session['messages'] = messages
    conn.close()
    return session


def complete_review_session(session_id):
    conn = get_db()
    _execute(conn, 'UPDATE review_sessions SET status=? WHERE id=?', ('completed', session_id))
    conn.commit()
    conn.close()


def get_all_review_sessions(user_id):
    conn = get_db()
    rows = _fetchall(conn,
        'SELECT id, date, user_problem, status, created_at FROM review_sessions WHERE user_id = ? ORDER BY date DESC',
        (user_id,))
    conn.close()
    return rows


# --- Note Summaries ---

def save_note_summary(user_id, date, summary):
    conn = get_db()
    if USE_PG:
        _execute(conn,
            '''INSERT INTO note_summaries (user_id, date, summary, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT (user_id, date) DO UPDATE SET summary=EXCLUDED.summary, created_at=EXCLUDED.created_at''',
            (user_id, date, summary, datetime.now().isoformat()))
    else:
        _execute(conn,
            'INSERT OR REPLACE INTO note_summaries (user_id, date, summary, created_at) VALUES (?, ?, ?, ?)',
            (user_id, date, summary, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_note_summary(user_id, date):
    conn = get_db()
    row = _fetchone(conn, 'SELECT * FROM note_summaries WHERE user_id = ? AND date = ?', (user_id, date))
    conn.close()
    return row


def save_user_token(user_id, github_token):
    conn = get_db()
    now = datetime.now().isoformat()
    if USE_PG:
        _execute(conn,
            '''INSERT INTO user_settings (user_id, github_token, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT (user_id) DO UPDATE SET github_token=EXCLUDED.github_token, updated_at=EXCLUDED.updated_at''',
            (user_id, github_token, now))
    else:
        _execute(conn,
            'INSERT OR REPLACE INTO user_settings (user_id, github_token, updated_at) VALUES (?, ?, ?)',
            (user_id, github_token, now))
    conn.commit()
    conn.close()


def get_user_token(user_id):
    conn = get_db()
    row = _fetchone(conn, 'SELECT github_token FROM user_settings WHERE user_id = ?', (user_id,))
    conn.close()
    return row['github_token'] if row and row.get('github_token') else None


def get_note_summaries_by_range(user_id, date_from, date_to):
    conn = get_db()
    rows = _fetchall(conn,
        'SELECT * FROM note_summaries WHERE user_id = ? AND date >= ? AND date <= ? ORDER BY date DESC',
        (user_id, date_from, date_to))
    conn.close()
    return rows
