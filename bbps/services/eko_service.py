import requests
import json
import time
import base64
import hmac
import hashlib
from django.conf import settings
from django.utils import timezone
import logging
from decimal import Decimal
import os
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class EkobbpsService:
    def __init__(self):
        self.base_url = "https://api.eko.in:25002/ekoicici/v2"
        self.developer_key = os.getenv("EKO_DEVELOPER_KEY")
        self.access_key = os.getenv("EKO_SECRET_KEY")
        self.initiator_id = os.getenv("EKO_INITIATOR_ID")
        self.user_code = os.getenv("EKO_USER_CODE")

        self.timeout = 30

    
    def _generate_timestamp(self):
        """Generate timestamp in milliseconds"""
        return str(int(time.time() * 1000))
    
    def _generate_signature(self, timestamp, concat_string=None):
        """Generate secret-key and request-hash"""
        # 1. Generate SECRET-KEY
        # Important: In Ruby code: encoded_key = Base64.strict_encode64(access_key)
        encoded_key = base64.b64encode(self.access_key.encode()).decode()
        
        # secret_key_hmac = OpenSSL::HMAC.digest("SHA256", encoded_key, timestamp)
        # secret_key = Base64.strict_encode64(secret_key_hmac)
        secret_key_hmac = hmac.new(
            encoded_key.encode(),
            timestamp.encode(),
            hashlib.sha256
        ).digest()
        secret_key = base64.b64encode(secret_key_hmac).decode()
        
        # 2. Generate REQUEST-HASH if concat_string provided
        request_hash = None
        if concat_string:
            # In Ruby: request_hash_hmac = OpenSSL::HMAC.digest("SHA256", encoded_key, concat_string)
            # request_hash = Base64.strict_encode64(request_hash_hmac)
            request_hash_hmac = hmac.new(
                encoded_key.encode(),
                concat_string.encode(),
                hashlib.sha256
            ).digest()
            request_hash = base64.b64encode(request_hash_hmac).decode()
        
        return secret_key, request_hash
    
    def _get_headers(self, timestamp, secret_key, request_hash=None):
        """Generate headers for API request"""
        headers = {
            "developer_key": self.developer_key,
            "secret-key-timestamp": timestamp,
            "secret-key": secret_key,
            "Content-Type": "application/json",
            "accept": "application/json"
        }
        
        # For operators endpoint, request_hash might not be needed
        if request_hash:
            headers["request_hash"] = request_hash
        
        return headers
    
    def _make_request(self, method, endpoint, payload=None, concat_string=None):
        """Make API request to EKO"""
        timestamp = self._generate_timestamp()
        secret_key, request_hash = self._generate_signature(timestamp, concat_string)
        headers = self._get_headers(timestamp, secret_key, request_hash)
        
        url = f"{self.base_url}{endpoint}"
        
        logger.info(f"EKO API Request: {method} {url}")
        logger.info(f"Headers: {headers}")
        logger.info(f"Payload: {payload}")
        
        try:
            if method.upper() == "POST":
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                    verify=False  # EKO uses self-signed certificate
                )
            elif method.upper() == "GET":
                response = requests.get(
                    url,
                    headers=headers,
                    params=payload,
                    timeout=self.timeout,
                    verify=False
                )
            else:
                return {"status": "error", "message": "Invalid HTTP method"}
            
            logger.info(f"EKO API Response Status: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
            try:
                return response.json()
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "message": "Invalid JSON response",
                    "raw_response": response.text,
                    "status_code": response.status_code
                }
                
        except requests.exceptions.Timeout:
            logger.error("EKO API request timeout")
            return {"status": "error", "message": "Request timeout"}
        except requests.exceptions.ConnectionError:
            logger.error("EKO API connection error")
            return {"status": "error", "message": "Connection error"}
        except Exception as e:
            logger.error(f"EKO API request error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def fetch_operators(self, category="prepaid"):
        """Fetch operators by category"""
        category_map = {
            "broadband": 1,     
            "gas": 2,            
            "dth": 4,               
            "prepaid": 5,       
            "tax": 6,        
            "credit": 7,         
            "electricity": 8,        
            "landline": 9,            
            "postpaid": 10,         
            "water": 11,     
            "society": 12,          
            "ott": 13,            
            "education": 14,    
            "municipal_tax": 15,    
            "clubs": 16,           
            "cable": 17,       
            "lpg": 18,          
            "hospital": 19,          
            "insurance": 20,      
            "loan": 21,   
            "fastag": 22,         
            "municipal_services": 23, 
            "subscription_2": 24,  
        }


        category_id = category_map.get(category.lower(), 5)
        endpoint = f"/billpayments/operators?category={category_id}"
        
        return self._make_request("GET", endpoint)
    
    def fetch_operator_locations(self):
        """Fetch operator locations"""
        endpoint = "/billpayments/operators_location"
        return self._make_request("GET", endpoint)
    
    def fetch_bill(self, operator_id, utility_acc_no, mobile_no, sender_name, client_ref_id):
        """Fetch bill details (for postpaid/utility bills)"""
        endpoint = f"/billpayments/fetchbill?initiator_id={self.initiator_id}"
        
        payload = {
            "source_ip": "121.121.1.1",
            "user_code": self.user_code,
            "client_ref_id": client_ref_id,
            "utility_acc_no": utility_acc_no,
            "confirmation_mobile_no": mobile_no,
            "sender_name": sender_name,
            "operator_id": operator_id,
            "latlong": "28.6139,77.2090",
            "hc_channel": "0",
            "mobile_number": mobile_no
        }
        
        # Generate concat string for request_hash
        timestamp = self._generate_timestamp()
        concat_string = f"{timestamp}{utility_acc_no}0{self.user_code}"
        
        return self._make_request("POST", endpoint, payload, concat_string)
    
    def bbps(self, mobile, amount, operator_id, client_ref_id, circle=None):
        """Perform bbps or bill payment"""
        endpoint = f"/billpayments/paybill?initiator_id={self.initiator_id}"
        
        payload = {
            "source_ip": "121.121.1.1",
            "user_code": self.user_code,
            "amount": str(amount),
            "client_ref_id": client_ref_id,
            "utility_acc_no": mobile,
            "confirmation_mobile_no": mobile,
            "sender_name": "Customer",
            "operator_id": operator_id,
            "latlong": "28.6139,77.2090",
            "hc_channel": 1
        }
        
        # Add circle if provided
        if circle:
            payload["circle"] = circle
        
        # Generate concat string for request_hash
        timestamp = self._generate_timestamp()
        concat_string = f"{timestamp}{mobile}{amount}{self.user_code}"
        
        return self._make_request("POST", endpoint, payload, concat_string)
    
    def check_status(self, transaction_ref):
        """Check transaction status"""
        endpoint = f"/billpayments/transaction/status"
        
        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.user_code,
            "transaction_ref": transaction_ref
        }
        
        return self._make_request("POST", endpoint, payload)

class bbpsManager:
    def __init__(self):
        self.eko_service = EkobbpsService()
    
    def get_operators(self, category="prepaid"):
        """Get operators by category"""
        response = self.eko_service.fetch_operators(category)
        
        # Check if response is valid and contains data
        if isinstance(response, dict) and "data" in response:
            operators = response.get("data", [])
            
            # Process operators to match our expected format
            processed_operators = []
            for op in operators:
                processed_operators.append({
                    "operator_id": str(op.get("operator_id", "")),
                    "name": op.get("name", ""),
                    "operator_name": op.get("name", ""),
                    "category_id": op.get("operator_category"),
                    "billFetchResponse": op.get("billFetchResponse", 0),
                    "high_commission_channel": op.get("high_commission_channel", 0),
                    "kyc_required": op.get("kyc_required", 0),
                    "location_id": op.get("location_id", 0),
                    "circle": op.get("circle", ""),
                    "state": op.get("state", ""),
                    "location": op.get("location", "")
                })
            
            return {
                "success": True,
                "category": category,
                "operators": processed_operators
            }
        
        return {
            "success": False,
            "message": "Failed to fetch operators or invalid response format",
            "data": response
        }
    
    def get_operator_locations(self):
        """Get operator locations"""
        response = self.eko_service.fetch_operator_locations()
        
        if isinstance(response, dict) and response.get("status") == "success":
            return {
                "success": True,
                "locations": response.get("data", [])
            }
        
        return {
            "success": False,
            "message": response.get("message", "Failed to fetch locations"),
            "data": response
        }
    
    def fetch_bill_details(self, operator_id, mobile, account_no=None, sender_name="Customer"):
        """Fetch bill details for postpaid/utility"""
        from uuid import uuid4
        
        client_ref_id = f"BILL{uuid4().hex[:8].upper()}"
        utility_acc_no = account_no if account_no else mobile
        
        response = self.eko_service.fetch_bill(
            operator_id=operator_id,
            utility_acc_no=utility_acc_no,
            mobile_no=mobile,
            sender_name=sender_name,
            client_ref_id=client_ref_id
        )
        
        if isinstance(response, dict):
            return {
                "success": True,
                "client_ref_id": client_ref_id,
                "data": response
            }
        
        return {
            "success": False,
            "message": "Failed to fetch bill details",
            "data": response
        }
    
    def perform_bbps(self, mobile, amount, operator_id, user=None, circle=None):
        """Perform bbps transaction"""
        from uuid import uuid4
        import random
        
        client_ref_id = f"TXN{uuid4().hex[:8].upper()}"
        
        # Make API call
        response = self.eko_service.bbps(
            mobile=mobile,
            amount=amount,
            operator_id=operator_id,
            client_ref_id=client_ref_id,
            circle=circle
        )
        
        # Process response
        result = {
            "success": False,
            "client_ref_id": client_ref_id,
            "eko_response": response,
            "transaction_id": f"RECH{int(time.time())}{random.randint(100, 999)}"
        }
        
        if isinstance(response, dict):
            # Extract values from response
            tx_status_desc = response.get("data", {}).get("txstatus_desc")
            eko_message = response.get("message")
            response_status = response.get("response_status_id", 1)
            
            # Determine success
            is_success = False
            failure_message = None
            
            if response_status == 0:
                is_success = True
            elif tx_status_desc and tx_status_desc.lower() == "success":
                is_success = True
            elif tx_status_desc:
                failure_message = tx_status_desc
            elif eko_message:
                failure_message = eko_message
            else:
                failure_message = "bbps Failed"
            
            result["success"] = is_success
            result["message"] = failure_message if not is_success else "bbps successful"
            result["txstatus_desc"] = tx_status_desc
            result["eko_message"] = eko_message
            result["response_status"] = response_status
            
            # If success, extract transaction reference
            if is_success and response.get("data"):
                result["eko_transaction_ref"] = response["data"].get("transaction_ref")
        
        return result

bbps_manager = bbpsManager()