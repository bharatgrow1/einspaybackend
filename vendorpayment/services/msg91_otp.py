# import requests
# import random
# import logging
# from django.conf import settings
# from django.utils import timezone
# from vendorpayment.models import VendorOTP

# logger = logging.getLogger(__name__)

# class MSG91OTPProvider:

#     def send_otp(self, mobile):
#         try:
#             mobile = mobile[-10:]  # always safe

#             otp = str(random.randint(100000, 999999))

#             VendorOTP.objects.update_or_create(
#                 vendor_mobile=mobile,
#                 defaults={
#                     "otp": otp,
#                     "expires_at": timezone.now() + timezone.timedelta(minutes=10),
#                     "is_verified": False
#                 }
#             )

#             payload = {
#                 "template_id": settings.MSG91_TEMPLATE_ID,
#                 "short_url": 0,
#                 "realTimeResponse": 1,
#                 "recipients": [
#                     {
#                         "mobiles": f"91{mobile}",
#                         "VAR1": otp
#                     }
#                 ]
#             }

#             headers = {
#                 "authkey": settings.MSG91_AUTH_KEY,
#                 "accept": "application/json",
#                 "content-type": "application/json"
#             }

#             response = requests.post(
#                 "https://control.msg91.com/api/v5/flow",
#                 json=payload,
#                 headers=headers,
#                 timeout=10
#             )

#             logger.info(f"MSG91 OTP => {response.status_code} {response.text}")

#             return {
#                 "success": response.status_code == 200,
#                 "provider": "msg91",
#                 "msg91_response": response.text
#             }

#         except Exception as e:
#             logger.error(f"MSG91 OTP error: {e}")
#             return {"success": False, "error": str(e)}



#     def verify_otp(self, mobile, otp):
#         try:
#             record = VendorOTP.objects.get(
#                 vendor_mobile=mobile,
#                 otp=otp,
#                 is_verified=False
#             )

#             if record.is_expired():
#                 return {"success": False, "error": "OTP expired"}

#             record.mark_verified()
#             return {"success": True}

#         except VendorOTP.DoesNotExist:
#             return {"success": False, "error": "Invalid OTP"}
