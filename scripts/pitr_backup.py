import os
import shutil
import time
from pathlib import Path
import sqlite3

# Configuration
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "app" / "data" / "mavuno.db"
BACKUP_DIR = BASE_DIR / "backups"
MAX_BACKUPS = 10

def create_backup():
    """Creates a timestamped backup of the SQLite database."""
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / f"mavuno_backup_{timestamp}.db"
    
    try:
        # Use sqlite3 backup API for a clean backup even if DB is busy
        with sqlite3.connect(DB_PATH) as conn:
            dst = sqlite3.connect(backup_path)
            with dst:
                conn.backup(dst)
            dst.close()
        
        print(f"✓ Backup created: {backup_path.name}")
        _cleanup_old_backups()
    except Exception as e:
        print(f"✗ Backup failed: {e}")

def restore_latest():
    """Restores the most recent backup."""
    if not BACKUP_DIR.exists():
        print("Error: No backups directory found.")
        return

    backups = sorted(list(BACKUP_DIR.glob("mavuno_backup_*.db")), reverse=True)
    if not backups:
        print("Error: No backup files found.")
        return

    latest = backups[0]
    print(f"Restoring from {latest.name}...")
    
    # Ensure app/data exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Backup current DB just in case before overwrite
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, DB_PATH.with_suffix(".db.old"))
        
    shutil.copy2(latest, DB_PATH)
    print("✓ Restore complete.")

def _cleanup_old_backups():
    """Keeps only the most recent MAX_BACKUPS."""
    backups = sorted(list(BACKUP_DIR.glob("mavuno_backup_*.db")))
    if len(backups) > MAX_BACKUPS:
        to_delete = backups[:-MAX_BACKUPS]
        for b in to_delete:
            b.unlink()
            print(f"Deleted old backup: {b.name}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        restore_latest()
    else:
        create_backup()
