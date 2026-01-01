from .smsdealnow_otp import SMSDealNowOTPProvider

class OTPRouter:
    def __init__(self):
        self.provider = SMSDealNowOTPProvider()

    def send_otp(self, mobile):
        return self.provider.send_otp(mobile)

    def verify_otp(self, mobile, otp):
        return self.provider.verify_otp(mobile, otp)

otp_router = OTPRouter()
