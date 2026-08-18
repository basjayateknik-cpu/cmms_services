from app import create_app
from models import db, LogsheetTemplate, LogsheetTemplateParameter

app = create_app()

with app.app_context():
    # Only create new tables
    LogsheetTemplate.__table__.create(db.engine, checkfirst=True)
    LogsheetTemplateParameter.__table__.create(db.engine, checkfirst=True)
    print("Logsheet templates tables created successfully.")
