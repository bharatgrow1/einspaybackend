import requests
import time
import base64
import hmac
import hashlib
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EkoVendorService:
    BASE_URL = "https://api.eko.in:25002/ekoicici"
    DEVELOPER_KEY = "753595f07a59eb5a52341538fad5a63d"
    ACCESS_KEY = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
    INITIATOR_ID = "9212094999"
    USER_CODE = "38130001"

    def generate_secret(self):
        ts = str(int(time.time() * 1000))
        encoded = base64.b64encode(self.ACCESS_KEY.encode()).decode()
        hashed = hmac.new(encoded.encode(), ts.encode(), hashlib.sha256).digest()
        secret = base64.b64encode(hashed).decode()
        return secret, ts

    def make_request(self, method, endpoint, data=None):
        secret, timestamp = self.generate_secret()

        headers = {
            "developer_key": self.DEVELOPER_KEY,
            "secret-key": secret,
            "secret-key-timestamp": timestamp,
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded"
        }

        url = self.BASE_URL + endpoint

        if method == "POST":
            response = requests.post(url, headers=headers, data=data)
        elif method == "GET":
            response = requests.get(url, headers=headers, params=data)
        else:
            raise ValueError("Invalid method")

        return response.json()

    def initiate_payment(self, payload):
        endpoint = f"/v1/agent/user_code:{self.USER_CODE}/settlement"
        return self.make_request("POST", endpoint, payload)
    
    
    def verify_bank_details(self, ifsc_code, account_number, retailer_mobile, customer_name):
        endpoint = f"/v2/banks/ifsc:{ifsc_code}/accounts/{account_number}"

        data = {
            "initiator_id": self.INITIATOR_ID,
            "customer_id": retailer_mobile,
            "user_code": self.USER_CODE
        }

        result = self.make_request("POST", endpoint, data)

        if result.get("status") != 0:
            return {
                "success": False,
                "verified": False,
                "error": result.get("message", "Bank verification failed"),
                "data": result
            }

        bank_data = result.get("data", {})
        api_name = bank_data.get("recipient_name", "").strip().upper()
        input_name = customer_name.strip().upper()

        return {
            "success": True,
            "verified": True,
            "bank_name": bank_data.get("bank", ""),
            "account_holder_name": api_name,
            "name_match": self._compare_names(api_name, input_name),
            "data": bank_data
        }

    def _compare_names(self, n1, n2):
        if n1 == n2:
            return True
        if n1 in n2 or n2 in n1:
            return True

        s1, s2 = set(n1.split()), set(n2.split())
        return len(s1 & s2) >= min(len(s1), len(s2)) / 2


bank_verifier = EkoVendorService()