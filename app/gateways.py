"""Production Gateways for Mavuno Protocol.

Handles real-world connectivity:
- USSD/SMS via AfricasTalking
- Payments via Flutterwave
"""

from __future__ import annotations
import os
import httpx
from .config import PUBLIC_BASE_URL

# --- Configuration (Load from ENV) ---
AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY", "")
FW_SECRET_KEY = os.getenv("FW_SECRET_KEY", "")

# --- USSD & SMS (AfricasTalking) ---
try:
    import africastalking

    _HAS_AT = True
except ImportError:
    _HAS_AT = False

if _HAS_AT and AT_API_KEY:
    africastalking.initialize(AT_USERNAME, AT_API_KEY)
    sms_service = africastalking.SMS
else:
    sms_service = None


def send_sms(phone: str, message: str):
    """Sends a real SMS if configured, otherwise logs to terminal."""
    if sms_service:
        try:
            sms_service.send(message, [phone])
        except Exception as e:
            print(f"[SMS ERROR] {str(e)}")
    else:
        print(f"[MOCK SMS to {phone}] {message}")


# --- Payments (Flutterwave) ---
async def initiate_fw_payment(
    payment_id: str, amount: int, phone: str, email: str = "farmer@mavuno.app"
):
    """
    Initiates a real Flutterwave Mobile Money transaction.
    Returns the redirect URL or transaction reference.
    """
    if not FW_SECRET_KEY:
        print(f"[MOCK PAY] FW Secret Key missing. Simulating payment {payment_id}")
        return {"status": "mock_success", "ref": "MOCK-REF-123"}

    url = "https://api.flutterwave.com/v3/payments"
    headers = {"Authorization": f"Bearer {FW_SECRET_KEY}"}
    payload = {
        "tx_ref": payment_id,
        "amount": str(amount),
        "currency": "UGX",
        "redirect_url": f"{PUBLIC_BASE_URL}/payments/confirm",
        "customer": {"email": email, "phonenumber": phone, "name": "Mavuno Farmer"},
        "customizations": {
            "title": "Mavuno Yield Settlement",
            "description": f"Payment for Offer {payment_id}",
        },
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            return resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}


async def verify_fw_transaction(tx_id: str):
    """Verifies a transaction using the Flutterwave ID."""
    if not FW_SECRET_KEY:
        return {"status": "success"}

    url = f"https://api.flutterwave.com/v3/transactions/{tx_id}/verify"
    headers = {"Authorization": f"Bearer {FW_SECRET_KEY}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        return resp.json()
