import os
from app import create_app, db
from sqlalchemy import text

app = create_app()

def migrate():
    with app.app_context():
        print("Migrating User table to add 'is_approved' column...")
        try:
            # Check if column exists
            result = db.session.execute(text("SHOW COLUMNS FROM user LIKE 'is_approved'"))
            column_exists = result.fetchone()
            
            if not column_exists:
                db.session.execute(text("ALTER TABLE user ADD COLUMN is_approved BOOLEAN DEFAULT FALSE"))
                print("Added column is_approved")
                
                db.session.execute(text("UPDATE user SET is_approved = TRUE"))
                db.session.commit()
                print("Updated existing users to is_approved = TRUE")
            else:
                print("Column is_approved already exists")
                
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()

if __name__ == "__main__":
    migrate()
