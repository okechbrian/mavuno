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
    if not _dst.exists() and _src.exists():
        import shutil
        shutil.copytree(_src, _dst)
    DATA_DIR = _dst
else:
    DATA_DIR = ROOT / "app" / "data"

# Optional dotenv
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# Require HMAC secret in production
_hmac_raw = os.getenv("HMAC_SECRET")
if not _hmac_raw and os.getenv("VERCEL"):
    raise RuntimeError("HMAC_SECRET is required in production.")
HMAC_SECRET = (_hmac_raw or "prototype-dev-key").encode()

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

# Security Hardening: Enforce passwords in environment.
AGENT_PASSWORD = os.getenv("AGENT_PASSWORD")
SUPERVISOR_PASSWORD = os.getenv("SUPERVISOR_PASSWORD")

if os.getenv("VERCEL") and (not AGENT_PASSWORD or not SUPERVISOR_PASSWORD):
    raise RuntimeError("AGENT_PASSWORD and SUPERVISOR_PASSWORD are required in production.")

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
