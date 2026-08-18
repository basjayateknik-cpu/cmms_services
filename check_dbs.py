import sqlite3

for db_name in ['cmms.db', 'app.db']:
    print(f"\nTables in {db_name}:")
    try:
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        print(c.fetchall())
        conn.close()
    except Exception as e:
        print(e)
