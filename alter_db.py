from app import create_app, db

app = create_app()

with app.app_context():
    from sqlalchemy import text
    try:
        db.session.execute(text('ALTER TABLE tasklist_procedure ADD COLUMN position INTEGER DEFAULT 0'))
        db.session.commit()
        print("Column 'position' added to tasklist_procedure")
    except Exception as e:
        db.session.rollback()
        print("Could not alter tasklist_procedure (maybe it exists):", e)
        
    try:
        db.session.execute(text('ALTER TABLE checklist_parameter_template ADD COLUMN position INTEGER DEFAULT 0'))
        db.session.commit()
        print("Column 'position' added to checklist_parameter_template")
    except Exception as e:
        db.session.rollback()
        print("Could not alter checklist_parameter_template (maybe it exists):", e)
