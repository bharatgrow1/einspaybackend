from .aeps_service import EkoAEPSService
from aeps.models import AEPSMerchant

class AEPSManager:
    def onboard_merchant(self, data):
        eko = EkoAEPSService()
        api = eko.onboard_merchant(data)

        if api.get("response_type_id") in [1290, 1307]:
            user_code = api["data"]["user_code"]

            if api.get("response_type_id") == 1290:
                AEPSMerchant.objects.create(
                    user_code=user_code,
                    merchant_name=f"{data['first_name']} {data.get('last_name', '')}".strip(),
                    shop_name=data["shop_name"],
                    mobile=data["mobile"],
                    email=data["email"],
                    pan_number=data["pan_number"],
                    address_line=data["address_line"],
                    city=data["city"],
                    state=data["state"],
                    pincode=data["pincode"],
                    district=data.get("district", ""),
                    area=data.get("area", "")
                )

            msg = "Merchant onboarded successfully" if api["response_type_id"] == 1290 else "Merchant already exists"

            return {
                "success": True,
                "message": msg,
                "user_code": user_code
            }

        return {
            "success": False,
            "message": api.get("message", "Onboarding failed"),
            "error": api
        }
    

    def get_available_services(self):
        eko = EkoAEPSService()
        return eko.get_services()
    

    def activate_aeps(self, data):
        eko = EkoAEPSService()
        return eko.activate_aeps_service(data)


    def request_otp(self, mobile):
        eko = EkoAEPSService()
        return eko.request_otp(mobile)
    

    def verify_mobile(self, mobile, otp):
        eko = EkoAEPSService()
        return eko.verify_user_mobile(mobile, otp)
    

    def user_services(self, user_code):
        eko = EkoAEPSService()
        return eko.user_services_enquiry(user_code)
    

    def get_wallet_balance(self, customer_id_type, customer_id, user_code=None):
        eko = EkoAEPSService()
        return eko.get_wallet_balance(customer_id_type, customer_id, user_code)



    def get_mcc_category(self, user_code):
        eko = EkoAEPSService()
        return eko.get_mcc_category(user_code)
    

    def get_states(self, user_code):
        eko = EkoAEPSService()
        return eko.get_states(user_code)
    



