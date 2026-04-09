import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/tracker_data.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS activity (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT NOT NULL,
                app_name    TEXT,
                window_title TEXT,
                screen_id   INTEGER DEFAULT 0,
                screen_label TEXT DEFAULT 'main',
                url         TEXT,
                task_category TEXT,
                focus_score INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS switch_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT NOT NULL,
                from_app    TEXT,
                to_app      TEXT,
                from_screen INTEGER DEFAULT 0,
                to_screen   INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_activity_ts ON activity(ts);
        """)

def insert_activity(app_name, window_title, screen_id, screen_label,
                    url=None, task_category=None, focus_score=0):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO activity
              (ts, app_name, window_title, screen_id, screen_label, url, task_category, focus_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), app_name, window_title,
              screen_id, screen_label, url, task_category, focus_score))

def insert_switch(from_app, to_app, from_screen, to_screen):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO switch_events (ts, from_app, to_app, from_screen, to_screen)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), from_app, to_app, from_screen, to_screen))

def query_today_summary():
    today = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        apps = conn.execute("""
            SELECT app_name, screen_label, COUNT(*) as seconds, task_category
            FROM activity WHERE ts >= ?
            GROUP BY app_name, screen_label ORDER BY seconds DESC LIMIT 20
        """, (today,)).fetchall()
        categories = conn.execute("""
            SELECT task_category, COUNT(*) as seconds
            FROM activity WHERE ts >= ? AND task_category IS NOT NULL
            GROUP BY task_category ORDER BY seconds DESC
        """, (today,)).fetchall()
        hourly = conn.execute("""
            SELECT strftime('%H', ts) as hour, screen_label, task_category, COUNT(*) as seconds
            FROM activity WHERE ts >= ?
            GROUP BY hour, screen_label, task_category ORDER BY hour
        """, (today,)).fetchall()
        switches = conn.execute("""
            SELECT COUNT(*) as cnt FROM switch_events WHERE ts >= ?
        """, (today,)).fetchone()
        focus = conn.execute("""
            SELECT app_name, task_category, MIN(ts) as start_ts, MAX(ts) as end_ts,
                   COUNT(*) as seconds, AVG(focus_score) as avg_score
            FROM (
                SELECT *, ROW_NUMBER() OVER (ORDER BY ts) -
                          ROW_NUMBER() OVER (PARTITION BY app_name ORDER BY ts) as grp
                FROM activity WHERE ts >= ?
            )
            GROUP BY app_name, grp HAVING seconds >= 300
            ORDER BY seconds DESC LIMIT 10
        """, (today,)).fetchall()
        screens = conn.execute("""
            SELECT screen_label, COUNT(*) as seconds
            FROM activity WHERE ts >= ? GROUP BY screen_label
        """, (today,)).fetchall()
    return {
        "apps": [dict(r) for r in apps],
        "categories": [dict(r) for r in categories],
        "hourly": [dict(r) for r in hourly],
        "switches": switches["cnt"] if switches else 0,
        "focus_blocks": [dict(r) for r in focus],
        "screens": [dict(r) for r in screens],
    }
