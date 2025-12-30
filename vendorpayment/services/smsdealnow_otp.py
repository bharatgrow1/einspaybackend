import requests
import random
import logging
import urllib.parse
from django.conf import settings
from django.utils import timezone
from vendorpayment.models import VendorOTP

logger = logging.getLogger(__name__)

class SMSDealNowOTPProvider:

    def send_otp(self, mobile):
        try:
            mobile = mobile[-10:]
            otp = str(random.randint(100000, 999999))

            VendorOTP.objects.update_or_create(
                vendor_mobile=mobile,
                defaults={
                    "otp": otp,
                    "expires_at": timezone.now() + timezone.timedelta(minutes=10),
                    "is_verified": False
                }
            )

            message = (
                f"{otp} is your OTP to add a new beneficiary. "
                f"This OTP is valid for 10 minutes. Please do not share it. KWIKPE"
            )

            encoded_msg = urllib.parse.quote(message)

            url = (
                "http://smsdealnow.com/api/pushsms"
                f"?user={settings.SMSDEALNOW_USER}"
                f"&authkey={settings.SMSDEALNOW_AUTH_KEY}"
                f"&sender={settings.SMSDEALNOW_SENDER_ID}"
                f"&mobile=91{mobile}"
                f"&text={encoded_msg}"
                f"&entityid={settings.SMSDEALNOW_ENTITY_ID}"
                f"&templateid={settings.SMSDEALNOW_TEMPLATE_ID}"
                f"&rpt=1"
            )

            response = requests.get(url, timeout=10)
            response_json = response.json()

            logger.info(f"SMSDEALNOW OTP => {response_json}")

            code = response_json.get("RESPONSE", {}).get("CODE")
            status = response_json.get("STATUS")

            success = code in ("100", "150") and status == "OK"

            return {
                "success": success,
                "provider": "smsdealnow",
                "code": code,
                "uid": response_json.get("RESPONSE", {}).get("UID")
            }

        except Exception as e:
            logger.error(e)
            return {"success": False, "error": str(e)}


    def verify_otp(self, mobile, otp):
        try:
            record = VendorOTP.objects.get(
                vendor_mobile=mobile[-10:],
                otp=otp,
                is_verified=False
            )

            if record.is_expired():
                return {"success": False, "error": "OTP expired"}

            record.mark_verified()
            return {"success": True}

        except VendorOTP.DoesNotExist:
            return {"success": False, "error": "Invalid OTP"}
