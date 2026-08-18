from app import create_app
from models import db
from sqlalchemy import text

def alter_db():
    app = create_app()
    with app.app_context():
        try:
            # Check if column exists first
            result = db.session.execute(text("SHOW COLUMNS FROM logsheet_schedule LIKE 'team_id';")).fetchone()
            if not result:
                db.session.execute(text("ALTER TABLE logsheet_schedule ADD COLUMN team_id INTEGER;"))
                db.session.execute(text("ALTER TABLE logsheet_schedule ADD CONSTRAINT fk_logsheet_schedule_team FOREIGN KEY (team_id) REFERENCES team(id);"))
                db.session.commit()
                print("Successfully added team_id to logsheet_schedule")
            else:
                print("team_id column already exists.")
        except Exception as e:
            print(f"Error adding team_id: {e}")
            db.session.rollback()

if __name__ == '__main__':
    alter_db()
