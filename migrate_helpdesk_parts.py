from app import create_app
from models import db, HelpdeskPart

app = create_app()
with app.app_context():
    print("Creating HelpdeskPart table...")
    HelpdeskPart.__table__.create(db.engine, checkfirst=True)
    print("Table created successfully.")
