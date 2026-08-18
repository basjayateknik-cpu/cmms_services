from app import create_app
from models import db

app = create_app()

with app.app_context():
    print("Creating helpdesk_ticket_technician table...")
    # Get the table definition from models mapping
    table = db.metadata.tables.get('helpdesk_ticket_technician')
    
    if table is not None:
        table.create(db.engine, checkfirst=True)
        print("Table created successfully or already exists.")
    else:
        print("Error: Table definition not found in metadata.")
