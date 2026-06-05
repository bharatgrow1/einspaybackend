import requests
import time
import base64
import hmac
import hashlib
import json
import uuid

# =========================
# EKO CONFIG
# =========================

BASE_URL = "https://api.eko.in:25002/ekoicici"

DEVELOPER_KEY = "753595f07a59eb5a52341538fad5a63d"
ACCESS_KEY = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"

USER_CODE = "38130001"
INITIATOR_ID = "9212094999"

# =========================
# PAYMENT DETAILS
# =========================

payload = {
    "initiator_id": INITIATOR_ID,
    "client_ref_id": f"LOCAL{uuid.uuid4().hex[:10]}",
    "service_code": 45,
    "payment_mode": 5,

    # CHANGE THESE
    "recipient_name": "PRITESH PRASAD",
    "account": "9924000100007471",
    "ifsc": "PUNB0992400",

    "amount": "10.00",

    "source": "NEWCONNECT",
    "sender_name": "VendorService App"
}

# =========================
# SECRET GENERATOR
# =========================

def generate_secret():

    timestamp = str(int(time.time() * 1000))

    encoded_key = base64.b64encode(
        ACCESS_KEY.encode()
    ).decode()

    hashed = hmac.new(
        encoded_key.encode(),
        timestamp.encode(),
        hashlib.sha256
    ).digest()

    secret = base64.b64encode(hashed).decode()

    return secret, timestamp

# =========================
# GENERATE AUTH
# =========================

secret, timestamp = generate_secret()

headers = {
    "developer_key": DEVELOPER_KEY,
    "secret-key": secret,
    "secret-key-timestamp": timestamp,
    "accept": "application/json",
    "content-type": "application/x-www-form-urlencoded"
}

# =========================
# API URL
# =========================

url = f"{BASE_URL}/v1/agent/user_code:{USER_CODE}/settlement"

# =========================
# PRINT DEBUG
# =========================

print("\n==============================")
print("EKO DIRECT PAYMENT TEST")
print("==============================\n")

print("URL:")
print(url)

print("\nHEADERS:")
print(json.dumps(headers, indent=2))

print("\nPAYLOAD:")
print(json.dumps(payload, indent=2))

print("\n==============================")
print("SENDING REQUEST...")
print("==============================\n")

# =========================
# SEND REQUEST
# =========================

try:

    response = requests.post(
        url,
        headers=headers,
        data=payload,
        timeout=60
    )

    print("STATUS CODE:")
    print(response.status_code)

    print("\nRAW RESPONSE:")
    print(response.text)

    try:
        json_response = response.json()

        print("\nJSON RESPONSE:")
        print(json.dumps(json_response, indent=2))

        print("\n==============================")
        print("RESULT")
        print("==============================")

        status = json_response.get("status")
        message = json_response.get("message")

        if status == 0:
            print(f"\n✅ PAYMENT SUCCESS")
            print(f"MESSAGE: {message}")

        else:
            print(f"\n❌ PAYMENT FAILED")
            print(f"STATUS: {status}")
            print(f"MESSAGE: {message}")

    except Exception as e:
        print("\n❌ JSON PARSE ERROR")
        print(str(e))

except Exception as e:
    print("\n❌ REQUEST FAILED")
    print(str(e))