"""Mavuno Social — public feed posts, reactions, and flag-and-hide moderation.

Mirrors the thin-data-layer shape of `app/chat.py` and `app/payments.py`:
no FastAPI coupling, all routes live in `app/main.py`. Every post body is
PII-redacted at write time via `crp._redact_pii`. Banned-word list lives at
`app/data/banned_words.json` (loaded once, mutation requires process
restart — fine for the demo window).

Ledger events: `POST_CREATED`, `POST_REACTED`, `POST_FLAGGED`, `VERIFIED_HARVEST`.
Payloads include structural identifiers only — never the post body.
"""
from __future__ import annotations
import json
import secrets
import time
from pathlib import Path
from typing import Optional

from . import crp, database, ledger, scorer

BODY_MAX = 300
ALLOWED_EMOJI = {"\U0001f331", "\U0001f525", "❤️", "\U0001f44f"}  # 🌱 🔥 ❤️ 👏
# Accept the un-variation-selector heart too, because browsers are messy.
ALLOWED_EMOJI.add("❤")

_BANNED_PATH = database.DATA_DIR / "banned_words.json"
try:
    _BANNED_WORDS = [
        w.lower() for w in json.loads(_BANNED_PATH.read_text()).get("banned", []) if w
    ]
except (FileNotFoundError, json.JSONDecodeError):
    _BANNED_WORDS = []


def _new_post_id() -> str:
    return "P-" + secrets.token_hex(3).upper()


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


def _contains_banned(text: str) -> bool:
    t = text.lower()
    return any(b in t for b in _BANNED_WORDS)


def create_post(farm_id: str, body: str, photo_url: Optional[str] = None, is_verified: bool = False) -> dict:
    body = (body or "").strip()
    if not body:
        return {"error": "empty_body"}
    if len(body) > BODY_MAX:
        return {"error": "body_too_long"}
    if _contains_banned(body):
        return {"error": "banned_word"}

    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM farms WHERE id = ?", (farm_id,))
    if not cur.fetchone():
        conn.close()
        return {"error": "unknown_farm"}

    safe_body = crp._redact_pii(body)
    pid = _new_post_id()
    now = int(time.time())
    is_verified_int = 1 if is_verified else 0
    cur.execute(
        """INSERT INTO posts (id, farm_id, body, photo_url, is_verified, created_at, hidden)
           VALUES (?, ?, ?, ?, ?, ?, 0)""",
        (pid, farm_id, safe_body, photo_url, is_verified_int, now),
    )
    conn.commit()
    conn.close()

    ledger.write("POST_CREATED", {"post_id": pid, "farm_id": farm_id})
    if is_verified_int:
        ledger.write("VERIFIED_HARVEST", {"post_id": pid, "farm_id": farm_id, "timestamp": now})

    return {
        "id": pid, "farm_id": farm_id, "body": safe_body,
        "photo_url": photo_url, "is_verified": is_verified_int,
        "created_at": now, "hidden": 0,
    }


def _hydrate(post_row) -> dict:
    """Attach farmer_name / district / crop + reaction counts to a raw post row."""
    conn = database.get_db()
    cur = conn.cursor()
    d = _row_to_dict(post_row)
    cur.execute(
        "SELECT farmer_name, district, crop FROM farms WHERE id = ?",
        (d["farm_id"],),
    )
    f = cur.fetchone()
    d["farmer_name"] = f["farmer_name"] if f else d["farm_id"]
    d["district"] = f["district"] if f else ""
    d["crop"] = f["crop"] if f else ""
    
    # YPS Flex
    try:
        score = scorer.score_farm(d["farm_id"])
        d["yps"] = score.get("yps")
    except Exception:
        d["yps"] = None

    cur.execute(
        """SELECT emoji, count(*) AS n FROM reactions
           WHERE post_id = ? GROUP BY emoji""",
        (d["id"],),
    )
    d["reactions"] = {r["emoji"]: int(r["n"]) for r in cur.fetchall()}
    conn.close()
    return d


def feed(limit: int = 50, district: Optional[str] = None) -> list[dict]:
    """Reverse-chrono, excludes hidden posts. Hydrated with farm + reactions. Geo-fenced by district if provided."""
    conn = database.get_db()
    cur = conn.cursor()
    
    if district:
        cur.execute(
            """SELECT p.* FROM posts p
               JOIN farms f ON p.farm_id = f.id
               WHERE p.hidden = 0 AND f.district = ?
               ORDER BY p.created_at DESC LIMIT ?""",
            (district, int(limit)),
        )
    else:
        cur.execute(
            """SELECT * FROM posts WHERE hidden = 0
               ORDER BY created_at DESC LIMIT ?""",
            (int(limit),),
        )
    
    rows = cur.fetchall()
    conn.close()
    return [_hydrate(r) for r in rows]


def get_post(post_id: str) -> Optional[dict]:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return _hydrate(row)


def react(post_id: str, reactor_role: str, reactor_id: str, emoji: str) -> dict:
    if reactor_role not in ("farmer", "buyer", "agent"):
        return {"error": "invalid_role"}
    if emoji not in ALLOWED_EMOJI:
        return {"error": "invalid_emoji"}

    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, hidden FROM posts WHERE id = ?", (post_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"error": "unknown_post"}
    if row["hidden"]:
        conn.close()
        return {"error": "post_hidden"}

    now = int(time.time())
    cur.execute(
        """INSERT OR IGNORE INTO reactions (post_id, reactor_role, reactor_id, emoji, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (post_id, reactor_role, reactor_id, emoji, now),
    )
    conn.commit()
    conn.close()
    ledger.write("POST_REACTED", {
        "post_id": post_id, "reactor_role": reactor_role,
        "reactor_id": reactor_id, "emoji": emoji,
    })
    return {"ok": True, "post_id": post_id, "emoji": emoji}


def flag(post_id: str, flagger_role: str, flagger_id: str, reason: Optional[str] = None) -> dict:
    if flagger_role not in ("farmer", "buyer", "agent"):
        return {"error": "invalid_role"}
    reason = (reason or "")[:200]

    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM posts WHERE id = ?", (post_id,))
    if not cur.fetchone():
        conn.close()
        return {"error": "unknown_post"}

    now = int(time.time())
    cur.execute(
        """INSERT OR IGNORE INTO post_flags
           (post_id, flagger_role, flagger_id, reason, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (post_id, flagger_role, flagger_id, reason, now),
    )
    # Any flag hides the post immediately (auto-moderation for the demo).
    cur.execute("UPDATE posts SET hidden = 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    ledger.write("POST_FLAGGED", {
        "post_id": post_id, "flagger_role": flagger_role,
        "flagger_id": flagger_id,
    })
    return {"ok": True, "post_id": post_id, "hidden": 1}
