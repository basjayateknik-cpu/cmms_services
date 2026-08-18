import sqlite3
import os

def run_recovery():
    db_path = 'backup/New folder/cmms.db'
    dump_path = 'backup/dump.sql'
    recovered_path = 'backup/cmms_recovered_new.db'
    
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    
    print("Dumping data to SQL script...")
    dumped_lines = []
    try:
        for line in conn.iterdump():
            dumped_lines.append(line)
        print("Dump finished successfully (no corruption encountered during read).")
    except Exception as e:
        print(f"Dump partially completed but hit an error: {e}")
        print("We will attempt to recover the data that was successfully dumped.")
    finally:
        conn.close()
        
    # Write dump to file
    with open(dump_path, 'w', encoding='utf-8') as f:
        # SQLite's iterdump returns BEGIN TRANSACTION but if it crashed, it might not have COMMIT.
        # We'll write what we have and ensure a COMMIT is at the end.
        has_commit = False
        for line in dumped_lines:
            f.write(line + '\n')
            if line.strip() == 'COMMIT;':
                has_commit = True
        
        if not has_commit:
            f.write("COMMIT;\n")

    print(f"SQL dump saved to {dump_path}.")
    
    if os.path.exists(recovered_path):
        os.remove(recovered_path)
        
    print(f"Restoring to new database {recovered_path}...")
    new_conn = sqlite3.connect(recovered_path)
    try:
        with open(dump_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
            # SQLite executescript allows running multiple statements
            new_conn.executescript(sql_script)
        print("Restore completed successfully!")
    except Exception as e:
        print(f"Error during restore: {e}")
    finally:
        new_conn.close()

if __name__ == '__main__':
    run_recovery()
