import os
from app import create_app
from models import db, HelpdeskModule, HelpdeskLocation

def seed_helpdesk_data():
    app = create_app()
    with app.app_context():
        # Seed Modules
        modules = ["Software", "Hardware", "Network", "Operational", "Other"]
        for mod_name in modules:
            if not HelpdeskModule.query.filter_by(name=mod_name).first():
                db.session.add(HelpdeskModule(name=mod_name))
                print(f"Added Module: {mod_name}")
        
        # Seed Locations
        locations = ["Building A", "Building B", "Main Office", "Warehouse", "Data Center"]
        for loc_name in locations:
            if not HelpdeskLocation.query.filter_by(name=loc_name).first():
                db.session.add(HelpdeskLocation(name=loc_name))
                print(f"Added Location: {loc_name}")
        
        db.session.commit()
        print("Helpdesk seeding complete!")

if __name__ == "__main__":
    seed_helpdesk_data()
