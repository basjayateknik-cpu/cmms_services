from app import create_app
from models import db, Shift, UserShift

app = create_app()

with app.app_context():
    db.create_all()
    print("Created Shift and UserShift tables successfully.")
