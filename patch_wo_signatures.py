import sqlite3

def patch_db():
    db_path = r'\\100.84.178.115\developing\cmms_app\cmms.db'
    print("Using DB path:", db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    columns = [
        "customer_name VARCHAR(100)",
        "customer_title VARCHAR(100)",
        "customer_signature TEXT",
        "technician_signature TEXT"
    ]
    
    for col in columns:
        try:
            cursor.execute(f"ALTER TABLE work_order ADD COLUMN {col}")
            print(f"Successfully added {col}.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {col} already exists.")
            else:
                print("Error:", e)
            
    conn.commit()
    conn.close()

if __name__ == '__main__':
    patch_db()
