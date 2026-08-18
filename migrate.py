from app import create_app, db
import sqlite3
import sqlalchemy

def migrate():
    app = create_app()
    app.app_context().push()
    
    print("Creating tables in MySQL...")
    db.create_all()
    
    print("Connecting to SQLite...")
    sqlite_conn = sqlite3.connect('temp.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in sqlite_cursor.fetchall() if row[0] != 'sqlite_sequence']
    
    print("Disabling foreign key checks in MySQL...")
    db.session.execute(sqlalchemy.text("SET FOREIGN_KEY_CHECKS=0;"))
    
    for table in tables:
        sqlite_cursor.execute(f'SELECT * FROM "{table}"')
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            continue
            
        col_names = [description[0] for description in sqlite_cursor.description]
        placeholders = ', '.join([':' + col for col in col_names])
        col_names_str = ', '.join([f'`{col}`' for col in col_names])
        
        insert_sql = f'INSERT IGNORE INTO `{table}` ({col_names_str}) VALUES ({placeholders})'
        
        print(f"Importing {len(rows)} rows into `{table}`...")
        
        for row in rows:
            row_dict = {col_names[i]: row[i] for i in range(len(col_names))}
            try:
                db.session.execute(sqlalchemy.text(insert_sql), row_dict)
            except Exception as e:
                print(f"Error inserting into {table}: {e}")
                
    print("Re-enabling foreign key checks...")
    db.session.execute(sqlalchemy.text("SET FOREIGN_KEY_CHECKS=1;"))
    db.session.commit()
    
    sqlite_conn.close()
    print("Migration completed successfully!")

if __name__ == '__main__':
    migrate()
