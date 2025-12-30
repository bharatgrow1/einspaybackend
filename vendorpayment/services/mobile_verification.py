import logging
from twilio.rest import Client
from django.conf import settings
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

class VendorMobileVerification:
    """Vendor mobile verification using Twilio"""
    
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.verify_service_sid = settings.TWILIO_VERIFY_SERVICE_SID
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        try:
            if self.account_sid and self.auth_token:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("✅ Twilio client initialized for vendor verification")
        except Exception as e:
            logger.error(f"❌ Twilio initialization failed: {e}")
            self.client = None
    
    def send_verification_otp(self, mobile):
        """Send OTP for vendor mobile verification"""
        try:
            if not self.client:
                return {
                    'success': False,
                    'error': 'Twilio client not initialized'
                }
            
            # Format mobile number
            formatted_mobile = self._format_mobile(mobile)
            
            # Send verification via SMS
            verification = self.client.verify \
                .v2 \
                .services(self.verify_service_sid) \
                .verifications \
                .create(to=formatted_mobile, channel='sms')
            
            logger.info(f"✅ OTP sent to vendor mobile: {mobile}")
            
            return {
                'success': True,
                'sid': verification.sid,
                'status': verification.status,
                'formatted_mobile': formatted_mobile
            }
            
        except TwilioRestException as e:
            logger.error(f"❌ Twilio error: {e}")
            return {
                'success': False,
                'error': f"Failed to send OTP: {e.msg}"
            }
        except Exception as e:
            logger.error(f"❌ Error sending OTP: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_otp(self, mobile, otp):
        """Verify OTP for vendor mobile"""
        try:
            if not self.client:
                return {
                    'success': False,
                    'error': 'Twilio client not initialized'
                }
            
            formatted_mobile = self._format_mobile(mobile)
            
            verification_check = self.client.verify \
                .v2 \
                .services(self.verify_service_sid) \
                .verification_checks \
                .create(to=formatted_mobile, code=otp)
            
            is_valid = verification_check.status == 'approved'
            
            logger.info(f"✅ OTP verification result: {verification_check.status}")
            
            return {
                'success': True,
                'valid': is_valid,
                'status': verification_check.status
            }
            
        except Exception as e:
            logger.error(f"❌ Error verifying OTP: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_mobile(self, mobile):
        """Format mobile number for Twilio"""
        if not mobile.startswith('+'):
            if mobile.startswith('91'):
                mobile = '+' + mobile
            else:
                mobile = '+91' + mobile
        return mobile

vendor_mobile_verifier = VendorMobileVerification()