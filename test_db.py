import sqlite3
import json

try:
    conn = sqlite3.connect('cmms.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, code, project_code FROM asset WHERE name LIKE '%WCP 16A%'")
    rows = cursor.fetchall()
    with open('db_output.txt', 'w') as f:
        f.write(json.dumps(rows, indent=2))
    print("Success")
except Exception as e:
    with open('db_output.txt', 'w') as f:
        f.write(str(e))
