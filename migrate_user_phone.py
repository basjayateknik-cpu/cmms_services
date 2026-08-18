from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text('ALTER TABLE user ADD COLUMN phone_number VARCHAR(20)'))
        db.session.commit()
        print("Column phone_number added to user table successfully.")
    except Exception as e:
        print(f"Error or column already exists: {e}")
        db.session.rollback()
