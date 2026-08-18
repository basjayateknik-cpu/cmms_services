from app import create_app
from models import db, HelpdeskTicketLog

app = create_app()

with app.app_context():
    HelpdeskTicketLog.__table__.create(db.engine, checkfirst=True)
    print("Database table HelpdeskTicketLog created successfully.")
