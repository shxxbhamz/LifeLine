import os
import django
from django.db import connection

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lifeline_backend.settings")
django.setup()

def run_sql_migrations():
    # Dynamically locate the Database/migrations folder
    migrations_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../Database/migrations"))
    
    if not os.path.exists(migrations_folder):
        print(f"Error: Directory not found -> {migrations_folder}")
        return

    # Find all .sql files and sort them case-insensitively (V1, v2, v3...)
    sql_files = sorted([f for f in os.listdir(migrations_folder) if f.endswith(".sql")], key=str.lower)
    
    if not sql_files:
        print("No .sql migration files found.")
        return

    print(f"Found {len(sql_files)} migration files. Executing against Neon...")

    with connection.cursor() as cursor:
        for file in sql_files:
            file_path = os.path.join(migrations_folder, file)
            print(f"Running migration: {file}...")
            
            with open(file_path, "r", encoding="utf-8") as f:
                sql_content = f.read()
                cursor.execute(sql_content)
                
            print(f"Successfully applied: {file}")

    print("All migrations executed successfully!")

if __name__ == "__main__":
    run_sql_migrations()