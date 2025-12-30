import time
import base64
import hmac
import hashlib
import json
import requests

class EkoAEPSService:
    BASE_URL = "https://api.eko.in:25002/ekoicici"
    DEVELOPER_KEY = "753595f07a59eb5a52341538fad5a63d"
    ACCESS_KEY = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
    INITIATOR_ID = "9212094999"

    def generate_secret(self):
        ts = str(int(time.time() * 1000))
        encoded_key = base64.b64encode(self.ACCESS_KEY.encode()).decode()
        hashed = hmac.new(encoded_key.encode(), ts.encode(), hashlib.sha256).digest()
        secret = base64.b64encode(hashed).decode()
        return secret, ts

    def onboard_merchant(self, merchant_data):
        secret, ts = self.generate_secret()

        headers = {
            "developer_key": self.DEVELOPER_KEY,
            "secret-key": secret,
            "secret-key-timestamp": ts,
            "content-type": "application/x-www-form-urlencoded",
            "accept": "application/json"
        }

        data = {
            "initiator_id": self.INITIATOR_ID,
            "pan_number": merchant_data["pan_number"],
            "mobile": merchant_data["mobile"],
            "first_name": merchant_data["first_name"],
            "middle_name": merchant_data.get("middle_name", ""),
            "last_name": merchant_data.get("last_name", ""),
            "email": merchant_data["email"],
            "dob": merchant_data["dob"],
            "shop_name": merchant_data["shop_name"],
            "residence_address": json.dumps({
                "line": merchant_data["address_line"],
                "city": merchant_data["city"],
                "state": merchant_data["state"],
                "pincode": merchant_data["pincode"],
            })
        }

        encoded = "&".join([f"{k}={v}" for k, v in data.items()])

        url = self.BASE_URL + "/v1/user/onboard"
        resp = requests.put(url, headers=headers, data=encoded)
        return resp.json()
    


    def get_services(self):
        secret, ts = self.generate_secret()

        headers = {
            "developer_key": self.DEVELOPER_KEY,
            "secret-key": secret,
            "secret-key-timestamp": ts,
            "accept": "application/json"
        }

        url = f"{self.BASE_URL}/v1/user/services?initiator_id={self.INITIATOR_ID}"

        resp = requests.get(url, headers=headers)
        return resp.json()
    


    def request_otp(self, mobile):
        secret, ts = self.generate_secret()

        headers = {
            "developer_key": self.DEVELOPER_KEY,
            "secret-key": secret,
            "secret-key-timestamp": ts,
            "content-type": "application/x-www-form-urlencoded",
            "accept": "application/json"
        }

        data = f"initiator_id={self.INITIATOR_ID}&mobile={mobile}"

        url = f"{self.BASE_URL}/v1/user/request/otp"

        resp = requests.put(url, headers=headers, data=data)
        return resp.json()
    


    def verify_user_mobile(self, mobile, otp):
        secret, ts = self.generate_secret()

        headers = {
            "developer_key": self.DEVELOPER_KEY,
            "secret-key": secret,
            "secret-key-timestamp": ts,
            "content-type": "application/x-www-form-urlencoded",
            "accept": "application/json"
        }

        data = f"initiator_id={self.INITIATOR_ID}&mobile={mobile}&otp={otp}"

        url = f"{self.BASE_URL}/v1/user/verify"

        resp = requests.put(url, headers=headers, data=data)
        return resp.json()
    



    def user_services_enquiry(self, user_code):
        secret, ts = self.generate_secret()

        headers = {
            "developer_key": self.DEVELOPER_KEY,
            "secret-key": secret,
            "secret-key-timestamp": ts,
            "accept": "application/json"
        }

        url = (f"{self.BASE_URL}/v1/user/services/"
            f"user_code:{user_code}?initiator_id={self.INITIATOR_ID}"
        )

        resp = requests.get(url, headers=headers)
        return resp.json()



    def get_wallet_balance(self, customer_id_type, customer_id, user_code=None):
        secret, ts = self.generate_secret()

        headers = {
            "developer_key": self.DEVELOPER_KEY,
            "secret-key": secret,
            "secret-key-timestamp": ts,
            "accept": "application/json"
        }

        url = (
            f"{self.BASE_URL}/v2/customers/"
            f"{customer_id_type}:{customer_id}/balance"
            f"?initiator_id={self.INITIATOR_ID}"
        )

        if user_code:
            url += f"&user_code={user_code}"

        resp = requests.get(url, headers=headers)
        return resp.json()



    
    def activate_aeps_service(self, data):
        secret, ts = self.generate_secret()

        url = f"{self.BASE_URL}/v1/user/service/activate"

        headers = {
            "developer_key": self.DEVELOPER_KEY,
            "secret-key": secret,
            "secret-key-timestamp": ts,
            "accept": "application/json"
        }

        form_data = {
            "initiator_id": self.INITIATOR_ID,
            "user_code": data["user_code"],
            "shop_type": data["shop_type"],
            "modelname": data["modelname"],
            "devicenumber": data["devicenumber"],
            "latlong": data["latlong"],
            "aadhar": data["aadhar"],
            "account": data["account"],
            "ifsc": data["ifsc"],
            "service_code": "43",
            "address_as_per_proof": json.dumps(data["address_as_per_proof"]),
            "office_address": json.dumps(data["office_address"])
        }

        files = {
            "pan_card": data["pan_card"],
            "aadhar_front": data["aadhar_front"],
            "aadhar_back": data["aadhar_back"]
        }

        resp = requests.put(url, headers=headers, data=form_data, files=files)
        return resp.json()



    def get_mcc_category(self, user_code):
        secret, ts = self.generate_secret()

        headers = {
            "developer_key": self.DEVELOPER_KEY,
            "secret-key": secret,
            "secret-key-timestamp": ts,
            "accept": "application/json"
        }

        url = (
            f"{self.BASE_URL}/v1/aeps/get-Mcc-Category"
            f"?initiator_id={self.INITIATOR_ID}&user_code={user_code}"
        )

        resp = requests.get(url, headers=headers)
        return resp.json()



    def get_states(self, user_code):
        secret, ts = self.generate_secret()

        headers = {
            "developer_key": self.DEVELOPER_KEY,
            "secret-key": secret,
            "secret-key-timestamp": ts,
            "accept": "application/json"
        }

        url = (
            f"{self.BASE_URL}/v1/aeps/get-states"
            f"?initiator_id={self.INITIATOR_ID}&user_code={user_code}"
        )

        resp = requests.get(url, headers=headers)
        return resp.json()
        
