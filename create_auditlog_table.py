from app import create_app
from models import db, AuditLog

app = create_app()

with app.app_context():
    AuditLog.__table__.create(db.engine, checkfirst=True)
    print("AuditLog table created successfully.")
