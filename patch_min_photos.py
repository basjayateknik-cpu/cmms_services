import sqlite3

db_path = 'cmms.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE tasklist_procedure ADD COLUMN min_photos INTEGER DEFAULT 0')
    print("Added min_photos to tasklist_procedure")
except Exception as e:
    print(f"tasklist_procedure error: {e}")

try:
    cursor.execute('ALTER TABLE work_order_procedure ADD COLUMN min_photos INTEGER DEFAULT 0')
    print("Added min_photos to work_order_procedure")
except Exception as e:
    print(f"work_order_procedure error: {e}")

conn.commit()
conn.close()
