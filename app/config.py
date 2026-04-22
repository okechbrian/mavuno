"""Central config + paths."""
from __future__ import annotations

import os
import secrets as _secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "app" / "static"

# On Vercel (and other serverless), the app bundle is read-only. Copy seed data
# into /tmp on first import so ledger.jsonl / tokens.jsonl writes succeed.
if os.getenv("VERCEL"):
    import shutil
    _src = ROOT / "app" / "data"
    _dst = Path("/tmp/mavuno_data")
    if not _dst.exists() and _src.exists():
        shutil.copytree(_src, _dst)
    DATA_DIR = _dst
else:
    DATA_DIR = ROOT / "app" / "data"

load_dotenv(ROOT / ".env")

_hmac_raw = os.getenv("HMAC_SECRET")
if not _hmac_raw:
    _hmac_raw = "dev-" + _secrets.token_hex(16)
    print("[mavuno] WARN: HMAC_SECRET env var not set — using ephemeral key", file=sys.stderr)
HMAC_SECRET = _hmac_raw.encode()
AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

# ECT policy
ECT_EXPIRY_HOURS = 72
ECT_GPS_RADIUS_KM = 5.0
# Credit tiering (YPS bucket -> kWh allocation)
TIER_KWH = {0: 0, 1: 25, 2: 60}
TIER_CEILING_UGX = {0: 0, 1: 75_000, 2: 200_000}
