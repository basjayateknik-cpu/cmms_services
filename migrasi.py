import os
from sqlalchemy import text, inspect
from app import create_app
from models import db

def run_migration():
    app = create_app()
    
    with app.app_context():
        print("Mengecek dan membuat tabel baru yang mungkin belum ada...")
        db.create_all()
        print("Tabel baru (jika ada) berhasil dibuat.\n")
        
        print("Mengecek kolom yang hilang di tabel-tabel yang sudah ada...")
        inspector = inspect(db.engine)
        
        for table_name, table in db.metadata.tables.items():
            if table_name not in inspector.get_table_names():
                continue
                
            db_columns = {col['name'] for col in inspector.get_columns(table_name)}
            
            for column in table.columns:
                if column.name not in db_columns:
                    print(f"-> Menambahkan kolom '{column.name}' ke tabel '{table_name}'...")
                    
                    try:
                        col_type_str = str(column.type.compile(db.engine.dialect))
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type_str}"
                        db.session.execute(text(sql))
                        db.session.commit()
                        print("   [OK] Berhasil")
                    except Exception as e:
                        db.session.rollback()
                        print(f"   [GAGAL] {e}")

        print("\nMigrasi Database selesai! Server sudah bisa dijalankan.")

if __name__ == '__main__':
    run_migration()
