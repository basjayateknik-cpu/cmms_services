from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Disabling foreign key checks...")
    db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    
    print("Truncating asset_meter_reading...")
    db.session.execute(text("TRUNCATE TABLE asset_meter_reading;"))
    
    print("Truncating asset_meter...")
    db.session.execute(text("TRUNCATE TABLE asset_meter;"))
    
    print("Enabling foreign key checks...")
    db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    
    db.session.commit()
    print("All metering assets and their readings have been deleted successfully.")
