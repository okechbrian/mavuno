"""Offer-scoped 1:1 messaging between buyers and farmers.

Mirrors the shape of `app/payments.py`: thin data-layer module, no FastAPI
coupling, all routes live in `app/main.py`. Persistence is SQLite through
`app.database.get_db()`. Every message body is PII-redacted at write time
using `crp._redact_pii`. Ledger events (`CHAT_OPEN`, `CHAT_MSG`) never carry
the body — only structural identifiers.
"""
from __future__ import annotations
import secrets
import time
from typing import Optional

from . import crp, database, ledger

BODY_MAX = 500


def _new_thread_id() -> str:
    return "TH-" + secrets.token_hex(3).upper()


def _new_message_id() -> str:
    return "MSG-" + secrets.token_hex(3).upper()


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


def open_thread(buyer_id: str, farm_id: str, offer_id: Optional[str] = None) -> dict:
    """Get-or-create a thread. Idempotent on (farm_id, buyer_id, offer_id).

    `offer_id` may be NULL (pre-deal chatter) — SQLite treats NULLs in a UNIQUE
    index as distinct, which is actually what we want (each new pre-deal chat
    that a buyer opens gets its own thread). The demo UI opens threads per-offer
    so this only matters in edge cases.
    """
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM farms WHERE id = ?", (farm_id,))
    if not cur.fetchone():
        conn.close()
        return {"error": "unknown_farm"}
    cur.execute("SELECT id FROM buyers WHERE id = ?", (buyer_id,))
    if not cur.fetchone():
        conn.close()
        return {"error": "unknown_buyer"}
    if offer_id is not None:
        cur.execute("SELECT id FROM offers WHERE id = ?", (offer_id,))
        if not cur.fetchone():
            conn.close()
            return {"error": "unknown_offer"}

    if offer_id is None:
        cur.execute(
            "SELECT * FROM chat_threads WHERE farm_id = ? AND buyer_id = ? AND offer_id IS NULL",
            (farm_id, buyer_id),
        )
    else:
        cur.execute(
            "SELECT * FROM chat_threads WHERE farm_id = ? AND buyer_id = ? AND offer_id = ?",
            (farm_id, buyer_id, offer_id),
        )
    row = cur.fetchone()
    if row:
        out = _row_to_dict(row)
        conn.close()
        return out

    tid = _new_thread_id()
    now = int(time.time())
    cur.execute(
        """INSERT INTO chat_threads
           (id, farm_id, buyer_id, offer_id, created_at, last_msg_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (tid, farm_id, buyer_id, offer_id, now, now),
    )
    conn.commit()
    cur.execute("SELECT * FROM chat_threads WHERE id = ?", (tid,))
    row = cur.fetchone()
    conn.close()

    ledger.write("CHAT_OPEN", {
        "thread_id": tid, "farm_id": farm_id,
        "buyer_id": buyer_id, "offer_id": offer_id,
    })
    return _row_to_dict(row)


def get_thread(thread_id: str) -> Optional[dict]:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chat_threads WHERE id = ?", (thread_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def send(thread_id: str, sender_role: str, sender_id: str, body: str) -> dict:
    """Append a message to a thread. Body is PII-redacted before persist.
    Caller is responsible for party-checking + rate-limiting."""
    if sender_role not in ("farmer", "buyer", "agent"):
        return {"error": "invalid_role"}
    body = (body or "").strip()
    if not body:
        return {"error": "empty_body"}
    if len(body) > BODY_MAX:
        return {"error": "body_too_long"}

    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chat_threads WHERE id = ?", (thread_id,))
    if not cur.fetchone():
        conn.close()
        return {"error": "unknown_thread"}

    safe_body = crp._redact_pii(body)
    mid = _new_message_id()
    now = int(time.time())
    cur.execute(
        """INSERT INTO chat_messages
           (id, thread_id, sender_role, sender_id, body, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (mid, thread_id, sender_role, sender_id, safe_body, now),
    )
    cur.execute(
        "UPDATE chat_threads SET last_msg_at = ? WHERE id = ?",
        (now, thread_id),
    )
    # Auto-advance the sender's read cursor — they obviously saw what they wrote.
    cur.execute(
        """INSERT INTO chat_read_cursors (thread_id, role, subject_id, last_read_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(thread_id, role, subject_id) DO UPDATE SET last_read_at = excluded.last_read_at""",
        (thread_id, sender_role, sender_id, now),
    )
    conn.commit()
    conn.close()

    ledger.write("CHAT_MSG", {
        "thread_id": thread_id, "sender_role": sender_role,
        "sender_id": sender_id, "msg_id": mid,
    })
    return {"id": mid, "thread_id": thread_id, "sender_role": sender_role,
            "sender_id": sender_id, "body": safe_body, "created_at": now}


def messages(thread_id: str, since_ts: int = 0, limit: int = 200) -> list[dict]:
    """Return messages in the thread with created_at > since_ts, oldest first."""
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM chat_messages
           WHERE thread_id = ? AND created_at > ?
           ORDER BY created_at ASC LIMIT ?""",
        (thread_id, since_ts, limit),
    )
    rows = [_row_to_dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _threads_with_preview(rows: list) -> list[dict]:
    """Given raw chat_threads rows, hydrate with counterpart names + last message."""
    if not rows:
        return []
    conn = database.get_db()
    cur = conn.cursor()
    out = []
    for r in rows:
        d = _row_to_dict(r)
        cur.execute("SELECT farmer_name FROM farms WHERE id = ?", (d["farm_id"],))
        f = cur.fetchone()
        d["farmer_name"] = f["farmer_name"] if f else d["farm_id"]
        cur.execute("SELECT name FROM buyers WHERE id = ?", (d["buyer_id"],))
        b = cur.fetchone()
        d["buyer_name"] = b["name"] if b else d["buyer_id"]
        cur.execute(
            """SELECT body, sender_role, created_at FROM chat_messages
               WHERE thread_id = ? ORDER BY created_at DESC LIMIT 1""",
            (d["id"],),
        )
        last = cur.fetchone()
        d["last_preview"] = last["body"][:120] if last else ""
        d["last_sender_role"] = last["sender_role"] if last else None
        out.append(d)
    conn.close()
    return out


def threads_for_farm(farm_id: str, limit: int = 50) -> list[dict]:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM chat_threads WHERE farm_id = ?
           ORDER BY last_msg_at DESC LIMIT ?""",
        (farm_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    threads = _threads_with_preview(rows)
    for t in threads:
        t["unread"] = _thread_unread(t["id"], "farmer", farm_id)
    return threads


def threads_for_buyer(buyer_id: str, limit: int = 50) -> list[dict]:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM chat_threads WHERE buyer_id = ?
           ORDER BY last_msg_at DESC LIMIT ?""",
        (buyer_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    threads = _threads_with_preview(rows)
    for t in threads:
        t["unread"] = _thread_unread(t["id"], "buyer", buyer_id)
    return threads


def threads_for_agent(limit: int = 200) -> list[dict]:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM chat_threads ORDER BY last_msg_at DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return _threads_with_preview(rows)


def _thread_unread(thread_id: str, role: str, subject_id: str) -> int:
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT last_read_at FROM chat_read_cursors
           WHERE thread_id = ? AND role = ? AND subject_id = ?""",
        (thread_id, role, subject_id),
    )
    cur_row = cur.fetchone()
    cursor_ts = cur_row["last_read_at"] if cur_row else 0
    cur.execute(
        """SELECT count(*) AS n FROM chat_messages
           WHERE thread_id = ? AND created_at > ? AND NOT (sender_role = ? AND sender_id = ?)""",
        (thread_id, cursor_ts, role, subject_id),
    )
    n = cur.fetchone()["n"]
    conn.close()
    return int(n or 0)


def unread_count(role: str, subject_id: str) -> int:
    """Sum of unread messages across all threads owned by this subject."""
    if role == "farmer":
        threads = [t["id"] for t in threads_for_farm(subject_id, limit=200)]
    elif role == "buyer":
        threads = [t["id"] for t in threads_for_buyer(subject_id, limit=200)]
    else:
        return 0
    return sum(_thread_unread(tid, role, subject_id) for tid in threads)


def mark_read(thread_id: str, role: str, subject_id: str) -> dict:
    now = int(time.time())
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO chat_read_cursors (thread_id, role, subject_id, last_read_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(thread_id, role, subject_id) DO UPDATE SET last_read_at = excluded.last_read_at""",
        (thread_id, role, subject_id, now),
    )
    conn.commit()
    conn.close()
    return {"thread_id": thread_id, "last_read_at": now}
