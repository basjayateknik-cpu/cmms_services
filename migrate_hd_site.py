
import sqlite3
import os

def migrate():
    # Database path
    db_path = 'cmms.db'
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add site_id to helpdesk_module
    print("Checking helpdesk_module table...")
    try:
        cursor.execute("ALTER TABLE helpdesk_module ADD COLUMN site_id INTEGER REFERENCES site(id)")
        print("Success: Added site_id to helpdesk_module")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Note: site_id already exists in helpdesk_module")
        else:
            print(f"Error updating helpdesk_module: {e}")

    # Add site_id to helpdesk_location
    print("Checking helpdesk_location table...")
    try:
        cursor.execute("ALTER TABLE helpdesk_location ADD COLUMN site_id INTEGER REFERENCES site(id)")
        print("Success: Added site_id to helpdesk_location")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Note: site_id already exists in helpdesk_location")
        else:
            print(f"Error updating helpdesk_location: {e}")

    conn.commit()
    conn.close()
    print("\nMigration script finished execution.")

if __name__ == "__main__":
    migrate()
