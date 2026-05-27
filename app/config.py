"""Central config + paths for Prototype."""
from __future__ import annotations
import os
import secrets as _secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "app" / "static"

# Vercel persistence handling
if os.getenv("VERCEL"):
    _src = ROOT / "app" / "data"
    _dst = Path("/tmp/mavuno_data")
    # Ensure fresh copy on each cold start to prevent stale/broken state
    if _src.exists():
        import shutil
        if _dst.exists():
            try:
                shutil.rmtree(_dst)
            except Exception:
                pass
        shutil.copytree(_src, _dst, dirs_exist_ok=True)
    DATA_DIR = _dst
else:
    DATA_DIR = ROOT / "app" / "data"

# Optional dotenv
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# HMAC secret for sessions and ledger
HMAC_SECRET = (os.getenv("HMAC_SECRET") or "mavuno-prototype-default-2026").encode()

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

# Security: Prefer environment variables, fall back to demo defaults for rapid prototyping.
AGENT_PASSWORD = os.getenv("AGENT_PASSWORD", "mavuno2026")
SUPERVISOR_PASSWORD = os.getenv("SUPERVISOR_PASSWORD", "governance2026")

# Default local SQLite path

DB_PATH = DATA_DIR / "mavuno.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Fix for Heroku/Render/Fly.io using 'postgres://' instead of 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Yield Priority policy
PRIORITY_EXPIRY_HOURS = 72
TIER_KG = {0: 0, 1: 25, 2: 60}
TIER_CEILING_UGX = {0: 0, 75000: 75_000, 200000: 200_000}
