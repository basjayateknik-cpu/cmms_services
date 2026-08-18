import sqlite3

def check():
    conn = sqlite3.connect('cmms.db')
    c = conn.cursor()
    c.execute('PRAGMA table_info(part)')
    print(c.fetchall())
    conn.close()

if __name__ == "__main__":
    check()
