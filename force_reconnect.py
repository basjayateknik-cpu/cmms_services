from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    result = db.session.execute(text("SHOW PROCESSLIST")).fetchall()
    count = 0
    for row in result:
        # row[0] is Id, row[4] is Command
        process_id = row[0]
        # don't kill our own connection
        if row[4] != 'Query':
            try:
                db.session.execute(text(f"KILL {process_id}"))
                count += 1
            except Exception as e:
                pass
    print(f"Killed {count} sleeping/other connections to force reconnect.")
