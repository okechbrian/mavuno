"""End-to-end verification for Mavuno Chat + Mavuno Social.

Run:  .venv-verify/Scripts/python scripts/verify_chat_social_e2e.py

Chat walk: buyer opens a thread, buyer message with a phone number is redacted
on write, farmer replies, buyer long-poll picks it up, second send in <2 s is
rate-limited, ledger gets CHAT_OPEN + CHAT_MSG rows that don't carry the body.

Social walk: farmer posts, buyer sees it in the feed, buyer reacts (dedupe),
buyer flags → post disappears, farmer post with a phone number is redacted,
banned-word post is rejected 400.
"""
from __future__ import annotations
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from fastapi.testclient import TestClient  # noqa: E402

from app import database  # noqa: E402
from app.main import app  # noqa: E402


def ok(label: str, cond: bool, detail: str = "") -> None:
    tag = "PASS" if cond else "FAIL"
    line = f"  [{tag}] {label}" + (f" -- {detail}" if detail else "")
    # Windows consoles are often cp1252 and cannot print emoji from response bodies;
    # fall back to ASCII with backslash-escapes.
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", "backslashreplace").decode("ascii"))
    if not cond:
        sys.exit(1)


def _login(client: TestClient, role: str, ident: str, pin: str) -> None:
    r = client.post("/login", json={"role": role, "id_or_phone": ident, "pin_or_password": pin})
    ok(f"{role} /login 200", r.status_code == 200, str(r.status_code))


def main() -> int:
    print("== Mavuno Chat + Social end-to-end verification ==\n")

    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM farms LIMIT 1")
    farm_row = cur.fetchone()
    cur.execute("SELECT id FROM buyers LIMIT 1")
    buyer_row = cur.fetchone()
    conn.close()
    ok("Seed farm exists", bool(farm_row))
    ok("Seed buyer exists", bool(buyer_row))
    farm_id = farm_row["id"]
    buyer_id = buyer_row["id"]
    print(f"  using farm={farm_id} · buyer={buyer_id}\n")

    farmer = TestClient(app)
    buyer = TestClient(app)
    agent = TestClient(app)
    _login(farmer, "farmer", farm_id, "1234")
    _login(buyer, "buyer", buyer_id, "1234")
    _login(agent, "agent", "", "mavuno2026")

    # ============================ CHAT WALK ================================
    print("\n-- Chat walk --")

    r = buyer.post("/chat/threads", json={"farm_id": farm_id})
    ok("POST /chat/threads 200", r.status_code == 200, r.text[:200])
    thread = r.json()
    ok("thread has id", "id" in thread, str(thread))
    tid = thread["id"]

    # Idempotent — same (buyer, farm, NULL offer) returns the same thread.
    r = buyer.post("/chat/threads", json={"farm_id": farm_id})
    ok("open_thread idempotent", r.json().get("id") == tid)

    # Buyer sends a message with a phone number; must be redacted on persist.
    raw_body = "is this Robusta? call me on 0701234567"
    r = buyer.post(f"/chat/{tid}/messages", json={"body": raw_body})
    ok("POST /chat/.../messages 200", r.status_code == 200, r.text[:200])
    msg = r.json()
    ok("returned body has [redacted]", "[redacted]" in msg["body"], msg["body"])
    ok("phone digits scrubbed", "0701234567" not in msg["body"], msg["body"])

    # Rate limit: same buyer sending again immediately -> 429.
    # Done early, before any other activity consumes the 2 s cooldown.
    r = buyer.post(f"/chat/{tid}/messages", json={"body": "one more quick one"})
    ok("rate-limit 429 on rapid resend", r.status_code == 429, str(r.status_code))
    time.sleep(2.1)

    # Farmer sees thread + unread badge.
    r = farmer.get("/chat/threads")
    ok("farmer GET /chat/threads 200", r.status_code == 200)
    farmer_threads = r.json().get("threads", [])
    my_thread = next((t for t in farmer_threads if t["id"] == tid), None)
    ok("farmer sees the thread", my_thread is not None)
    ok("farmer unread > 0", my_thread and my_thread.get("unread", 0) >= 1, str(my_thread))

    r = farmer.get("/chat/unread/count")
    ok("farmer unread count endpoint", r.status_code == 200 and r.json().get("count", 0) >= 1,
       str(r.json()))

    # Farmer reply — different sender_id, so not throttled.
    r = farmer.post(f"/chat/{tid}/messages", json={"body": "yes, Robusta, harvested last week"})
    ok("farmer reply 200", r.status_code == 200, r.text[:200])
    farmer_msg = r.json()

    # Buyer long-poll since the first buyer message should pick up the farmer reply.
    since_ts = msg["created_at"]
    r = buyer.get(f"/chat/{tid}/messages?since={since_ts}&wait=2")
    ok("buyer long-poll 200", r.status_code == 200)
    pulled = r.json().get("messages", [])
    ok("long-poll returns the farmer reply",
       any(m["id"] == farmer_msg["id"] for m in pulled), str(pulled))

    # Reading advances the buyer cursor — farmer's unread for that thread should be 0
    # after farmer also polls (below). First confirm buyer sees 0 unread now.
    r = farmer.get(f"/chat/{tid}/messages?since=0&wait=0")
    ok("farmer read flushes their own cursor", r.status_code == 200)
    r = farmer.get("/chat/unread/count")
    ok("farmer unread back to 0 after read", r.json().get("count", 99) == 0, str(r.json()))

    # Send another buyer message to confirm post-cooldown works (farmer reply path
    # + long-poll already burnt well over 2 s, so buyer bucket is clear now).
    r = buyer.post(f"/chat/{tid}/messages", json={"body": "bagging in 50 kg sacks ok?"})
    ok("after cooldown, send 200", r.status_code == 200, str(r.status_code))

    # Party check: a different buyer (try agent-as-non-party not applicable since agent passes).
    # Use an unauth client — must 401.
    anon = TestClient(app)
    r = anon.get(f"/chat/{tid}/messages?wait=0")
    ok("unauth chat read -> 401", r.status_code == 401, str(r.status_code))

    # Ledger: CHAT_OPEN + CHAT_MSG events exist; payload does NOT contain body.
    r = agent.get("/ledger")
    ok("GET /ledger 200 (agent)", r.status_code == 200)
    rows = r.json().get("rows", [])
    chat_events_for_thread = []
    for ev in rows:
        entry = ev.get("entry") or {}
        payload = entry.get("payload") or {}
        if payload.get("thread_id") == tid:
            chat_events_for_thread.append((entry.get("type"), payload))
    types = [t for (t, _) in chat_events_for_thread]
    ok("ledger has CHAT_OPEN", "CHAT_OPEN" in types, str(types))
    ok("ledger has CHAT_MSG", types.count("CHAT_MSG") >= 3, f"count={types.count('CHAT_MSG')}")
    ok("ledger never carries body",
       all("body" not in p for (_, p) in chat_events_for_thread),
       str(chat_events_for_thread[:2]))

    # ============================ SOCIAL WALK ==============================
    print("\n-- Social walk --")

    r = farmer.post("/feed", json={"body": "Harvest done, 200 kg Robusta ready"})
    ok("farmer POST /feed 200", r.status_code == 200, r.text[:200])
    post = r.json()
    pid = post["id"]

    r = buyer.get("/feed?limit=50")
    ok("buyer GET /feed 200", r.status_code == 200)
    posts = r.json().get("posts", [])
    ok("buyer sees the post", any(p["id"] == pid for p in posts))

    FIRE = "\U0001f525"
    ALIEN = "\U0001f47d"
    r = buyer.post(f"/feed/{pid}/react", json={"emoji": FIRE})
    ok("buyer reacts [fire]", r.status_code == 200, r.text[:200])

    # Dedupe: same emoji again -- upsert, no duplicate row.
    r = buyer.post(f"/feed/{pid}/react", json={"emoji": FIRE})
    ok("second same-emoji react 200 (idempotent)", r.status_code == 200)

    r = buyer.get(f"/feed/{pid}")
    ok("GET /feed/{id} 200", r.status_code == 200)
    detail = r.json()
    ok("reaction count is 1", detail.get("reactions", {}).get(FIRE) == 1,
       str(detail.get("reactions")))

    # Reject non-allowlisted emoji.
    r = buyer.post(f"/feed/{pid}/react", json={"emoji": ALIEN})
    ok("non-allowlisted emoji rejected", r.status_code == 400, str(r.status_code))

    # PII redaction on post body.
    r = farmer.post("/feed", json={"body": "call me at 0701234567 for pickup"})
    ok("farmer PII post 200", r.status_code == 200, r.text[:200])
    redacted_pid = r.json()["id"]
    r = buyer.get(f"/feed/{redacted_pid}")
    ok("PII in feed is redacted", "[redacted]" in r.json()["body"] and "0701234567" not in r.json()["body"],
       r.json()["body"])

    # Banned word → 400.
    r = farmer.post("/feed", json={"body": "you absolute idiot_farmer"})
    ok("banned-word post rejected", r.status_code == 400, str(r.status_code))

    # Flag → hide.
    r = buyer.post(f"/feed/{pid}/flag", json={"reason": "test flag"})
    ok("buyer flag 200", r.status_code == 200)
    r = buyer.get("/feed?limit=50")
    ok("flagged post no longer in /feed",
       all(p["id"] != pid for p in r.json().get("posts", [])), "still present")

    # Ledger: POST_CREATED + POST_FLAGGED; bodies never on chain.
    r = agent.get("/ledger")
    rows = r.json().get("rows", [])
    post_events = []
    for ev in rows:
        entry = ev.get("entry") or {}
        payload = entry.get("payload") or {}
        if payload.get("post_id") == pid:
            post_events.append((entry.get("type"), payload))
    types = [t for (t, _) in post_events]
    ok("ledger has POST_CREATED", "POST_CREATED" in types, str(types))
    ok("ledger has POST_FLAGGED", "POST_FLAGGED" in types, str(types))
    ok("ledger post payloads never carry body",
       all("body" not in p for (_, p) in post_events),
       str(post_events[:2]))

    # Only farmers may post.
    r = buyer.post("/feed", json={"body": "i'm a buyer posting"})
    ok("buyer POST /feed -> 403", r.status_code == 403, str(r.status_code))

    print("\nAll checks passed. Mavuno Chat + Social verified end-to-end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
