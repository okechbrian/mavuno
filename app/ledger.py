"""Append-only SHA-256 hash-chained JSONL ledger.

Each line is a JSON object with an 'entry' payload plus:
  prev_hash:  hex digest of the prior line's hash, or GENESIS for line 1
  hash:       sha256(prev_hash + canonical_json(entry))

Tampering with any prior entry invalidates every subsequent hash.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

from .config import DATA_DIR

LEDGER_PATH = DATA_DIR / "ledger.jsonl"
GENESIS = "0" * 64
_lock = threading.Lock()


def _canon(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _hash(prev: str, entry: dict) -> str:
    return hashlib.sha256((prev + _canon(entry)).encode()).hexdigest()


def _last_hash() -> str:
    if not LEDGER_PATH.exists():
        return GENESIS
    try:
        with LEDGER_PATH.open("r", encoding="utf-8") as f:
            last = None
            for line in f:
                line = line.strip()
                if line:
                    last = line
            if last is None:
                return GENESIS
            return json.loads(last)["hash"]
    except Exception:
        return GENESIS


def append(event_type: str, payload: dict) -> dict:
    """Append a new event. Returns the stored record."""
    with _lock:
        prev = _last_hash()
        entry = {"ts": int(time.time()), "type": event_type, "payload": payload}
        h = _hash(prev, entry)
        record = {"prev_hash": prev, "entry": entry, "hash": h}
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record


def read_all() -> list[dict]:
    if not LEDGER_PATH.exists():
        return []
    rows: list[dict] = []
    with LEDGER_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def verify() -> dict:
    """Re-hash the chain. Returns {ok, length, first_bad_line}."""
    prev = GENESIS
    rows = read_all()
    for i, row in enumerate(rows, start=1):
        if row["prev_hash"] != prev:
            return {"ok": False, "length": i, "first_bad_line": i, "reason": "prev_hash_mismatch"}
        expected = _hash(prev, row["entry"])
        if row["hash"] != expected:
            return {"ok": False, "length": i, "first_bad_line": i, "reason": "hash_mismatch"}
        prev = row["hash"]
    return {"ok": True, "length": len(rows)}
