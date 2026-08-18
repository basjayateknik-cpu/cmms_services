import os
from app import create_app
from models import db, DigitalSignature

app = create_app()

with app.app_context():
    # Attempt to create the table
    try:
        DigitalSignature.__table__.create(db.engine)
        print("DigitalSignature table created successfully!")
    except Exception as e:
        print(f"Error or table already exists: {e}")
