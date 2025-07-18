import sqlite3
from datetime import datetime, date

DB_PATH = "run_and_fup.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        # пользователи в разрезе групп
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            group_id INTEGER,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, group_id)
        )
        """)
        # пробежки с привязкой к группе
        c.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            user_id INTEGER,
            username TEXT,
            distance REAL,
            duration INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()

def ensure_user(group_id: int, user_id: int, username: str):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO users (user_id, group_id, username) VALUES (?, ?, ?)",
            (user_id, group_id, username)
        )
        conn.commit()

def add_run(group_id: int, user_id: int, username: str, distance: float, duration: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO runs (group_id, user_id, username, distance, duration) VALUES (?, ?, ?, ?, ?)",
            (group_id, user_id, username, distance, duration)
        )
        conn.commit()

def get_user_stats(group_id: int, user_id: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*), SUM(distance), SUM(duration) 
            FROM runs 
            WHERE group_id=? AND user_id=?
        """, (group_id, user_id))
        return c.fetchone()

def get_user_history(group_id: int, user_id: int, limit=5):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT distance, duration, created_at 
            FROM runs 
            WHERE group_id=? AND user_id=? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (group_id, user_id, limit))
        return c.fetchall()

def get_leaderboard(group_id: int, limit=10):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT username, SUM(distance) as total_km 
            FROM runs 
            WHERE group_id=?
            GROUP BY user_id 
            ORDER BY total_km DESC 
            LIMIT ?
        """, (group_id, limit))
        return c.fetchall()
    
def get_all_users_in_group(group_id: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, username FROM users WHERE group_id=?", (group_id,))
        return c.fetchall()

def get_users_with_runs_today(group_id: int):
    today = date.today().isoformat()
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT user_id FROM runs 
            WHERE group_id=? AND DATE(created_at)=?
        """, (group_id, today))
        return {row[0] for row in c.fetchall()}
