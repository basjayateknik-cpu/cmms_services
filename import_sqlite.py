import mysql.connector
import re

def import_sql():
    from app import create_app, db
    app = create_app()
    app.app_context().push()
    print("Creating tables via SQLAlchemy...")
    db.create_all()

    print("Connecting via mysql.connector...")
    conn = mysql.connector.connect(host='10.40.0.175', port=3305, user='jti_acr_bas', password='JTI_j0h@r10', database='cmms_db')
    cursor = conn.cursor()
    
    print("Reading CMMS.sql...")
    with open('CMMS.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
        
    statements = sql.split(';')
    inserts = [s.strip() for s in statements if s.strip().upper().startswith('INSERT INTO')]
    
    print(f"Found {len(inserts)} INSERT statements. Executing...")
    
    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
    cursor.execute("SET SQL_MODE='ANSI_QUOTES';")
    
    success = 0
    for stmt in inserts:
        try:
            cursor.execute(stmt)
            success += 1
        except Exception as e:
            print(f"Error on: {stmt[:100]}...\n{e}")
            
    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Import complete! Successfully executed {success}/{len(inserts)} statements.")

if __name__ == '__main__':
    import_sql()
