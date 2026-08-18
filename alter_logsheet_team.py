import sqlite3

def alter_db():
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    
    try:
        c.execute("ALTER TABLE logsheet_schedule ADD COLUMN team_id INTEGER REFERENCES team(id);")
        print("Successfully added team_id to logsheet_schedule")
    except Exception as e:
        print(f"Error adding team_id: {e}")
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    alter_db()
