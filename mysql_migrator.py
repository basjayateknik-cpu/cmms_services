import os
from dotenv import load_dotenv
load_dotenv()
import sqlite3
from sqlalchemy import create_engine, text, MetaData

# ==========================================
# CONFIGURATION - PLEASE UPDATE IF NEEDED
# ==========================================
SQLITE_DB_PATH = 'backup/cmms_recovered_new.db'
# Change this to match your actual MySQL database credentials
MYSQL_URI = os.environ.get('MIGRATOR_DB_URL')

def run_migration():
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"Error: {SQLITE_DB_PATH} not found. Please ensure your SQLite DB is there.")
        return

    print(f"Connecting to MySQL: {MYSQL_URI}")
    mysql_engine = create_engine(MYSQL_URI)
    
    # 1. Ensure MySQL tables exist
    # We will import `db` and `app` to let Flask-SQLAlchemy create all tables in MySQL
    try:
        os.environ['DATABASE_URL'] = MYSQL_URI; from app import create_app
        from models import db
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = MYSQL_URI
        with app.app_context():
            print("Creating tables in MySQL if they don't exist...")
            db.create_all()
    except Exception as e:
        print(f"Failed to create tables via app context: {e}")
        return

    # 2. Reflect the MySQL database schema
    metadata = MetaData()
    metadata.reflect(bind=mysql_engine)
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    with mysql_engine.begin() as mysql_conn:
        print("Disabling foreign key checks during migration...")
        mysql_conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))

        # Iterate over all tables in MySQL
        for table_name in metadata.tables.keys():
            # Skip alembic table if any
            if table_name == 'alembic_version':
                continue
                
            print(f"Migrating table '{table_name}'...")
            
            # Check if table exists in SQLite
            sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not sqlite_cursor.fetchone():
                print(f"  -> Skipped: Table '{table_name}' not found in SQLite.")
                continue
                
            # Read all data from SQLite
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print(f"  -> Skipped: No data in '{table_name}'.")
                continue

            # Clear existing data in MySQL table to avoid duplicates if run multiple times
            mysql_conn.execute(text(f"TRUNCATE TABLE {table_name};"))
            
            # Insert data into MySQL
            columns = rows[0].keys()
            table_obj = metadata.tables[table_name]
            
            # Filter columns that actually exist in MySQL
            valid_cols = [col for col in columns if col in table_obj.columns]
            
            if not valid_cols:
                continue

            insert_data = []
            for row in rows:
                row_dict = {}
                for col in valid_cols:
                    val = row[col]
                    # Handle specific type conversions if necessary
                    # If it's an empty string and the MySQL column is an Integer/Float, set to None
                    col_type_str = str(table_obj.columns[col].type).lower()
                    if val == '':
                        if 'int' in col_type_str or 'float' in col_type_str:
                            val = None
                    elif isinstance(val, str) and 'varchar' in col_type_str:
                        # Extract length from varchar(N)
                        import re
                        m = re.search(r'varchar\((\d+)\)', col_type_str)
                        if m:
                            max_len = int(m.group(1))
                            if len(val) > max_len:
                                val = val[:max_len]

                    row_dict[col] = val
                
                # Skip invalid rows for associative tables if primary key is None
                skip_row = False
                for pk_col in table_obj.primary_key.columns:
                    if row_dict.get(pk_col.name) is None:
                        skip_row = True
                        break
                if skip_row:
                    continue

                insert_data.append(row_dict)

            # Bulk insert
            try:
                mysql_conn.execute(table_obj.insert(), insert_data)
                print(f"  -> Successfully migrated {len(insert_data)} rows.")
            except Exception as e:
                print(f"  -> Error inserting into {table_name}: {e}")

        print("Re-enabling foreign key checks...")
        mysql_conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))

    sqlite_conn.close()
    print("\nMigration completed successfully!")
    print("Update your server's environment variable to use MySQL:")
    print(f"DATABASE_URL={MYSQL_URI}")

if __name__ == "__main__":
    run_migration()
