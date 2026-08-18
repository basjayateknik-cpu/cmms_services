import sqlite3
import json

def check():
    conn = sqlite3.connect('cmms.db')
    c = conn.cursor()
    c.execute('PRAGMA table_info(part)')
    cols = c.fetchall()
    with open('cols.json', 'w') as f:
        json.dump(cols, f)
    conn.close()

if __name__ == "__main__":
    check()
