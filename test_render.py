import os
from app import create_app, db
from models import Asset

app = create_app()

with app.app_context():
    from flask import render_template
    with app.test_request_context('/assets/2/view'):
        from flask_login import login_user
        from models import User
        # Login as an admin to pass @login_required
        admin = User.query.filter_by(role='Admin').first()
        if admin:
            login_user(admin)
            
        asset = Asset.query.get(2)
        if asset:
            try:
                from models import Part, Vendor, Checklist
                from datetime import datetime, timedelta
                parts = Part.query.all()
                users = User.query.all()
                vendors = Vendor.query.all()
                checklists = Checklist.query.all()
                render_template('assets/view.html', asset=asset, parts=parts, users=users, vendors=vendors, checklists=checklists, today=datetime.today().date(), timedelta=timedelta)
                print("Render successful!")
            except Exception as e:
                import traceback
                traceback.print_exc()
        else:
            print("Asset 2 not found")
