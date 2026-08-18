import sqlite3

def patch():
    conn = sqlite3.connect('cmms.db')
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE helpdesk_ticket ADD COLUMN asset VARCHAR(255)')
        print('Column asset added successfully.')
    except sqlite3.OperationalError as e:
        print(f'OperationalError: {e}')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    patch()
