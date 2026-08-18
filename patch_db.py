"""
Database patch script to add new columns for:
- AssetCustomField.expiry_date
- UserDashboardWidget (new table)
- CustomSidebarLink (new table)
"""
import os
from app import create_app
from models import db
import sqlalchemy

def patch_database():
    app = create_app()
    with app.app_context():
        # 1. Create new tables (UserDashboardWidget, CustomSidebarLink)
        print("Creating any new tables...")
        db.create_all()
        print("New tables created successfully.")
        
        # 2. Add expiry_date column to asset_custom_field if it doesn't exist
        try:
            db.session.execute(sqlalchemy.text(
                "ALTER TABLE asset_custom_field ADD COLUMN expiry_date DATETIME"
            ))
            db.session.commit()
            print("Added 'expiry_date' column to asset_custom_field.")
        except Exception as e:
            db.session.rollback()
            if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                print("Column 'expiry_date' already exists, skipping.")
            else:
                print(f"Note: {e}")
        
        print("Database patch complete!")

if __name__ == "__main__":
    patch_database()
