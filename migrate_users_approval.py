import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'cmms.db')

def migrate():
    print(f"Connecting to {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if the column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'is_approved' not in columns:
            print("Adding 'is_approved' column to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN is_approved BOOLEAN DEFAULT 0")
            
            print("Updating existing users to is_approved = 1 (True)...")
            cursor.execute("UPDATE user SET is_approved = 1")
            
            conn.commit()
            print("Migration successful.")
        else:
            print("'is_approved' column already exists.")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
