from app import create_app
from models import db, HelpdeskProgress, HelpdeskProgressFile

app = create_app()

with app.app_context():
    # Only create the newly added tables
    HelpdeskProgress.__table__.create(db.engine, checkfirst=True)
    HelpdeskProgressFile.__table__.create(db.engine, checkfirst=True)
    print("Database tables HelpdeskProgress and HelpdeskProgressFile created successfully.")

