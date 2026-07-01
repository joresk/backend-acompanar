import psycopg2

db_url = "postgresql://postgres:pintura1@localhost:5432/acompanar3"

def alter_table():
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Add columns for reset password
        sql1 = "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS reset_code VARCHAR(6);"
        sql2 = "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS reset_code_expires TIMESTAMP;"
        
        cursor.execute(sql1)
        cursor.execute(sql2)
        print("Successfully added reset_code and reset_code_expires to usuarios.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error executing ALTER TABLE: {e}")

if __name__ == "__main__":
    alter_table()
