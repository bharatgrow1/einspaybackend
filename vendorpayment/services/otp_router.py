from .smsdealnow_otp import SMSDealNowOTPProvider

class OTPRouter:
    def __init__(self):
        self.provider = SMSDealNowOTPProvider()

    def send_otp(self, mobile):
        return self.provider.send_otp(mobile)

    def verify_otp(self, mobile, otp):
        return self.provider.verify_otp(mobile, otp)

otp_router = OTPRouter()




# from django.conf import settings
# from .msg91_otp import MSG91OTPProvider
# from .mobile_verification import vendor_mobile_verifier

# class OTPRouter:
#     def __init__(self):
#         self.msg91 = MSG91OTPProvider()
#         self.twilio = vendor_mobile_verifier

#     def send_otp(self, mobile):
#         if settings.OTP_PROVIDER == "TWILIO":
#             return self.twilio.send_verification_otp(mobile)
#         return self.msg91.send_otp(mobile)

#     def verify_otp(self, mobile, otp):
#         if settings.OTP_PROVIDER == "TWILIO":
#             return self.twilio.verify_otp(mobile, otp)
#         return self.msg91.verify_otp(mobile, otp)

# otp_router = OTPRouter()
