# 📁 database.py
import sqlite3
import json

DB_FILE = "schedule_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_name TEXT,
            data TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_schedule_to_db(batch_name, data_dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    data_json = json.dumps(data_dict)
    cursor.execute("INSERT INTO schedules (batch_name, data) VALUES (?, ?)", (batch_name, data_json))
    conn.commit()
    conn.close()

def load_schedules_from_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT batch_name, data FROM schedules")
    rows = cursor.fetchall()
    conn.close()
    return [(name, json.loads(data)) for name, data in rows]
