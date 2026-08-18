import sqlite3
import os

DB_PATH = 'cmms.db'

def alter_db():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE work_order ADD COLUMN delay_reason TEXT")
        print("Successfully added delay_reason column to work_order table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column already exists.")
        else:
            print(f"Error: {e}")
            
    conn.commit()
    conn.close()

if __name__ == '__main__':
    alter_db()
