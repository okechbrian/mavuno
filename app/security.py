"""Security & Cryptography for Mavuno Prototype."""
import hmac
import hashlib
import time
import secrets
import json

# Prototype Secret - In production, this would be an env var
HMAC_SECRET = b"future-makers-hackathon-2026-secret-key"

def sign_token(token_id: str, farm_id: str, kwh: int) -> str:
    """Signs an Energy Credit Token with HMAC-SHA256."""
    msg = f"{token_id}:{farm_id}:{kwh}:{time.time()}"
    return hmac.new(HMAC_SECRET, msg.encode(), hashlib.sha256).hexdigest()

def hash_payload(payload_dict: dict) -> str:
    """Standard SHA-256 for ledger chaining."""
    payload_str = json.dumps(payload_dict, sort_keys=True)
    return hashlib.sha256(payload_str.encode()).hexdigest()

def chain_hash(prev_hash: str, payload_hash: str) -> str:
    """Creates a chained hash for the audit ledger."""
    return hashlib.sha256(f"{prev_hash}{payload_hash}".encode()).hexdigest()
