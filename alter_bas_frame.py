from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE bas_frame ADD COLUMN site_id INTEGER NULL REFERENCES site(id);"))
        db.session.commit()
        print("Column site_id added successfully.")
    except Exception as e:
        print(f"Error adding column: {e}")
