from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        # Add api columns to asset_meter
        db.session.execute(text("ALTER TABLE asset_meter ADD COLUMN api_url VARCHAR(500) NULL"))
        db.session.execute(text("ALTER TABLE asset_meter ADD COLUMN api_method VARCHAR(10) DEFAULT 'GET'"))
        db.session.execute(text("ALTER TABLE asset_meter ADD COLUMN api_json_key VARCHAR(255) NULL"))
        db.session.execute(text("ALTER TABLE asset_meter ADD COLUMN api_interval INT DEFAULT 5"))
        db.session.commit()
        print("Database altered successfully. Added API columns to asset_meter.")
    except Exception as e:
        db.session.rollback()
        print(f"Error altering database: {e}")
