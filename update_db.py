from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE part ADD COLUMN unit VARCHAR(50);"))
        db.session.commit()
        print("Column 'unit' added successfully to 'part' table.")
    except Exception as e:
        print(f"Error (maybe column already exists): {e}")
