import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "app" / "data" / "mavuno.db"
EXPORT_PATH = ROOT / "app" / "data" / "db_export.json"

def export_all():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row['name'] for row in cursor.fetchall() if row['name'] != 'sqlite_sequence']

    export_data = {}

    for table in tables:
        cursor.execute(f"SELECT * FROM {table}")
        rows = [dict(row) for row in cursor.fetchall()]
        export_data[table] = rows
        print(f"Exported {len(rows)} rows from {table}")

    with open(EXPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2)

    print(f"Full database exported to {EXPORT_PATH}")
    conn.close()

if __name__ == "__main__":
    export_all()
