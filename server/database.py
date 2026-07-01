"""Database module for SQLite task management.

This module handles:
- SQLite database initialization
- Schema creation and migration
- Connection management

Database path: data/db/tasks.db
"""

import sqlite3
import os

DATA_DIR = os.path.join(os.getcwd(), 'data', 'db')
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "tasks.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                login_id TEXT,
                password TEXT,
                chat_id TEXT,
                target_semester_code TEXT,
                interval INTEGER DEFAULT 300,
                status TEXT DEFAULT 'stopped', 
                pid INTEGER,
                position INTEGER DEFAULT 0,
                monitor_type TEXT DEFAULT 'nilai',
                target_courses TEXT,
                whatsapp_number TEXT,
                notify_without_grades_telegram INTEGER DEFAULT 0,
                notify_without_grades_whatsapp INTEGER DEFAULT 0)''')
    upgrade_db()
    conn.commit()
    conn.close()

def upgrade_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("PRAGMA table_info(tasks)")
    columns = [info[1] for info in c.fetchall()]
    
    if 'position' not in columns:
        print("[INFO] Migrating database: Adding 'position' column...")
        c.execute("ALTER TABLE tasks ADD COLUMN position INTEGER DEFAULT 0")
        c.execute("UPDATE tasks SET position = id")
        
    if 'monitor_type' not in columns:
        print("[INFO] Migrating database: Adding 'monitor_type' column...")
        c.execute("ALTER TABLE tasks ADD COLUMN monitor_type TEXT DEFAULT 'nilai'")
        
    if 'target_courses' not in columns:
        print("[INFO] Migrating database: Adding 'target_courses' column...")
        c.execute("ALTER TABLE tasks ADD COLUMN target_courses TEXT")

    if 'whatsapp_number' not in columns:
        print("[INFO] Migrating database: Adding 'whatsapp_number' column...")
        c.execute("ALTER TABLE tasks ADD COLUMN whatsapp_number TEXT")

    if 'notify_without_grades_telegram' not in columns:
        print("[INFO] Migrating database: Adding 'notify_without_grades_telegram' column...")
        c.execute("ALTER TABLE tasks ADD COLUMN notify_without_grades_telegram INTEGER DEFAULT 0")

    if 'notify_without_grades_whatsapp' not in columns:
        print("[INFO] Migrating database: Adding 'notify_without_grades_whatsapp' column...")
        c.execute("ALTER TABLE tasks ADD COLUMN notify_without_grades_whatsapp INTEGER DEFAULT 0")
        
        
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
