import requests
import json
import time
import base64
import hmac
import hashlib
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EkoAPIService:
    def __init__(self):
        self.base_url = "https://api.eko.in:25002/ekoicici"
        
        self.developer_key = "753595f07a59eb5a52341538fad5a63d"
        self.access_key = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
        self.initiator_id = "9212094999"
        self.EKO_USER_CODE = "38130001"
        self.timeout = 30

    def generate_signature(self, concat_string=None):
        timestamp = str(int(time.time() * 1000))
        encoded_key = base64.b64encode(self.access_key.encode()).decode()

        hashed = hmac.new(encoded_key.encode(), timestamp.encode(), hashlib.sha256).digest()
        secret_key = base64.b64encode(hashed).decode()

        request_hash = None
        if concat_string:
            rh = hmac.new(encoded_key.encode(), concat_string.encode(), hashlib.sha256).digest()
            request_hash = base64.b64encode(rh).decode()

        return secret_key, timestamp, request_hash

    def get_headers(self, concat_string=None):
        secret_key, ts, request_hash = self.generate_signature(concat_string)

        headers = {
            "accept": "application/json",
            "developer_key": self.developer_key,
            "secret-key": secret_key,
            "secret-key-timestamp": ts,
            "content-type": "application/x-www-form-urlencoded"
        }

        if request_hash:
            headers["request_hash"] = request_hash

        return headers

    def make_request(self, method, endpoint, data=None, concat_string=None, force_json=False):
        url = f"{self.base_url}{endpoint}"

        # Default headers (form)
        headers = self.get_headers(concat_string)

        # If JSON forced (biometric case)
        if force_json:
            headers["content-type"] = "application/json"

        logger.info(f"EKO API Request: {method} {url}")
        logger.info(f"Headers: {headers}")
        logger.info(f"Payload: {data}")

        try:
            if method.upper() == "PUT":
                if force_json:
                    response = requests.put(url, json=data, headers=headers, timeout=self.timeout)
                else:
                    response = requests.put(url, data=data, headers=headers, timeout=self.timeout)

            elif method.upper() == "POST":
                if force_json:
                    response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
                else:
                    response = requests.post(url, data=data, headers=headers, timeout=self.timeout)

            elif method.upper() == "GET":
                response = requests.get(url, params=data, headers=headers, timeout=self.timeout)

            else:
                return {"status": 1, "message": "Invalid method"}

            logger.info(f"EKO API Response Status: {response.status_code}")
            logger.info(f"Response: {response.text}")

            try:
                return response.json()
            except json.JSONDecodeError:
                return {
                    "status": 1,
                    "message": "Invalid JSON response",
                    "raw_response": response.text
                }

        except Exception as e:
            logger.error(str(e))
            return {"status": 1, "message": str(e)}


    def onboard_user(self, user_data):
        """User Onboarding - PUT /v1/user/onboard"""
        endpoint = "/v1/user/onboard"

        residence_address_json = json.dumps(user_data["residence_address"])

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "pan_number": user_data["pan_number"],
            "mobile": user_data["mobile"],
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "email": user_data["email"],
            "residence_address": residence_address_json,
            "dob": user_data["dob"],
            "shop_name": user_data["shop_name"]
        }

        return self.make_request("PUT", endpoint, payload)
    


    def get_sender_profile(self, customer_mobile):
        """GET SENDER PROFILE - GET /v3/customer/profile/{customer_mobile}/dmt-fino"""
        endpoint = f"/v3/customer/profile/{customer_mobile}"
        
        params = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE
        }

        return self.make_request("GET", endpoint, data=params)
    


    def create_customer(self, customer_data):
        """
        Create Customer for DMT
        POST /v3/customer/account/{customer_id}/dmt-fino
        """
        customer_id = customer_data.get("mobile")
        
        if not customer_id:
            return {"status": 1, "message": "Customer mobile number is required"}
        
        endpoint = f"/v3/customer/account/{customer_id}/dmt-fino"
        
        residence_address = {
            "line": customer_data.get("address_line", "India"),
            "city": customer_data.get("city", ""),
            "state": customer_data.get("state", ""),
            "pincode": customer_data.get("pincode", ""),
            "district": customer_data.get("district", ""),
            "area": customer_data.get("area", "")
        }
        
        residence_address_json = json.dumps(residence_address)
        
        payload = {
            "initiator_id": self.initiator_id,
            "name": customer_data.get("name", ""),
            "user_code": self.EKO_USER_CODE,
            "dob": customer_data.get("dob", ""),
            "residence_address": residence_address_json
        }
        
        if customer_data.get("skip_verification"):
            payload["skip_verification"] = "true" 
        
        return self.make_request("POST", endpoint, payload)


    def verify_customer_identity(self, customer_mobile, otp, otp_ref_id):
        """Verify Customer OTP - CORRECT PAYLOAD FORMAT"""
        endpoint = "/v3/customer/account/otp/verify"
        
        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "customer_id": customer_mobile,
            "otp": str(otp),
            "otp_ref_id": otp_ref_id,
            "service_code": "80"
        }
        
        return self.make_request("POST", endpoint, payload)

    def resend_otp(self, customer_mobile):
        """Resend OTP - CORRECT ENDPOINT"""
        endpoint = f"/v2/customers/mobile_number:{customer_mobile}/otp"
        
        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE
        }
        
        return self.make_request("POST", endpoint, payload)



    def customer_ekyc_biometric(self, customer_id, aadhar, piddata):
        endpoint = f"/v3/customer/account/{customer_id}/dmt-fino/ekyc"

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "aadhar": aadhar,
            "piddata": piddata
        }

        return self.make_request("POST", endpoint, data=payload, force_json=True)




    def verify_ekyc_otp(self, customer_id, otp, otp_ref_id, kyc_request_id):
        endpoint = f"/v3/customer/account/{customer_id}/dmt-fino/otp/verify"

        payload = {
            "otp": otp,
            "otp_ref_id": otp_ref_id,
            "kyc_request_id": kyc_request_id,
            "user_code": self.EKO_USER_CODE,
            "initiator_id": self.initiator_id
        }

        return self.make_request("POST", endpoint, data=payload)

    def add_recipient(self, customer_id, recipient_name, recipient_mobile, account, ifsc, bank_id, recipient_type=3, account_type=1):
        """Add Recipient - CORRECT EKO DMT ENDPOINT"""
        
        endpoint = f"/v2/customers/mobile_number:{customer_id}/recipients/acc_ifsc:{account}_{ifsc}"
        
        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "recipient_name": recipient_name,
            "recipient_mobile": recipient_mobile,
            "recipient_type": str(recipient_type),
            "bank_id": str(bank_id) 
        }
        
        return self.make_request("PUT", endpoint, payload)

    def get_recipient_list(self, customer_id):
        """Get Recipient List - CORRECT ENDPOINT"""
        endpoint = f"/v2/customers/mobile_number:{customer_id}/recipients"
        
        params = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
        }
        
        return self.make_request("GET", endpoint, data=params)

    def send_transaction_otp(self, customer_id, recipient_id, amount):
        """Send Transaction OTP - CORRECT ENDPOINT"""
        endpoint = "/v3/customer/payment/dmt-fino/otp"
        
        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "customer_id": customer_id,
            "recipient_id": recipient_id,
            "amount": str(amount)
        }
        
        return self.make_request("POST", endpoint, payload)

    def initiate_transaction(self, customer_id, recipient_id, amount, otp, otp_ref_id):
        """Initiate Transaction - CORRECT EKO DMT ENDPOINT"""
        endpoint = "/v2/transactions"
        
        from datetime import datetime
        client_ref_id = f"TXN{int(time.time())}"
        
        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "customer_id": customer_id,
            "recipient_id": recipient_id,
            "amount": str(amount),
            "currency": "INR",
            "timestamp": datetime.now().isoformat(),
            "client_ref_id": client_ref_id,
            "channel": 2,
            "state": 1,
            "latlong": "28.6139,77.2090",
            "otp": otp,
            "otp_ref_id": otp_ref_id
        }
        
        return self.make_request("POST", endpoint, payload)
    


    def transaction_inquiry(self, inquiry_id, is_client_ref_id=False):
        """
        Transaction Inquiry
        GET /v1/transactions/{tid} OR /v1/transactions/client_ref_id:{client_ref_id}
        """
        if is_client_ref_id:
            endpoint = f"/v1/transactions/client_ref_id:{inquiry_id}"
        else:
            endpoint = f"/v1/transactions/{inquiry_id}"
        
        params = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE
        }
        
        return self.make_request("GET", endpoint, data=params)
    


    def refund_transaction(self, tid, otp):
        """
        Refund Transaction
        POST /v2/transactions/{tid}/refund
        """
        endpoint = f"/v2/transactions/{tid}/refund"
        
        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "otp": otp,
            "state": 1
        }
        
        return self.make_request("POST", endpoint, payload)
    

    def resend_refund_otp(self, tid):
        """
        Resend Refund OTP
        POST /v1/transactions/{tid}/refund/otp
        """
        endpoint = f"/v1/transactions/{tid}/refund/otp"
        
        payload = {
            "initiator_id": self.initiator_id
        }
        
        return self.make_request("POST", endpoint, payload)



eko_service = EkoAPIService()