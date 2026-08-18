import sqlite3
import mysql.connector

def migrate():
    print("Connecting to databases...")
    sqlite_conn = sqlite3.connect('temp.db')
    sqlite_cursor = sqlite_conn.cursor()

    mysql_conn = mysql.connector.connect(host='10.40.0.175', port=3305, user='jti_acr_bas', password='JTI_j0h@r10', database='cmms_db')
    mysql_cursor = mysql_conn.cursor()

    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in sqlite_cursor.fetchall() if row[0] != 'sqlite_sequence']

    mysql_cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

    for table in tables:
        if table == 'work_instruction_checklist':
            continue # Skip old table
            
        sqlite_cursor.execute(f'SELECT * FROM "{table}"')
        rows = sqlite_cursor.fetchall()
        if not rows: continue
        
        col_names = [desc[0] for desc in sqlite_cursor.description]
        
        # Get MySQL columns for this table
        mysql_cursor.execute(f'SHOW COLUMNS FROM `{table}`')
        mysql_cols = [c[0] for c in mysql_cursor.fetchall()]
        
        # Find matching columns
        col_indices = [i for i, c in enumerate(col_names) if c in mysql_cols]
        final_cols = [col_names[i] for i in col_indices]
        
        if not final_cols: continue
        
        # Filter rows to only matching columns
        final_rows = [tuple(row[i] for i in col_indices) for row in rows]
        
        placeholders = ', '.join(['%s'] * len(final_cols))
        col_names_str = ', '.join([f'`{c}`' for c in final_cols])
        
        insert_sql = f'INSERT IGNORE INTO `{table}` ({col_names_str}) VALUES ({placeholders})'
        
        try:
            mysql_cursor.executemany(insert_sql, final_rows)
        except Exception as e:
            print(f'Error inserting into {table}: {e}')

    mysql_cursor.execute('SET FOREIGN_KEY_CHECKS=1;')
    mysql_conn.commit()
    print('Migration completed successfully!')

if __name__ == '__main__':
    migrate()
