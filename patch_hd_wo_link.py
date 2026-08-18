import sqlite3
import os

def patch_db():
    db_path = r'\\100.84.178.115\developing\cmms_app\cmms.db'
    print("Using DB path:", db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE work_order ADD COLUMN helpdesk_ticket_id INTEGER REFERENCES helpdesk_ticket(id)")
        print("Successfully added helpdesk_ticket_id to work_order.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column helpdesk_ticket_id already exists.")
        else:
            print("Error:", e)
            
    conn.commit()
    conn.close()

if __name__ == '__main__':
    patch_db()
