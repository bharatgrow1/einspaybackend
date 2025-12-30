from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.verify_service_sid = getattr(settings, 'TWILIO_VERIFY_SERVICE_SID', None)
        self.client = None
        
        logger.info(f"🔧 Twilio Config - SID: {self.account_sid}, Service SID: {self.verify_service_sid}")
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Twilio client with error handling"""
        try:
            if not self.account_sid or not self.auth_token:
                logger.error("❌ Twilio credentials missing in settings")
                logger.error(f"Account SID: {self.account_sid}")
                logger.error(f"Auth Token: {'*' * len(self.auth_token) if self.auth_token else 'None'}")
                return
            
            self.client = Client(self.account_sid, self.auth_token)
            
            # Test the connection by fetching the verify service
            service = self.client.verify.v2.services(self.verify_service_sid).fetch()
            logger.info(f"✅ Twilio client initialized successfully. Service: {service.friendly_name}")
            
        except TwilioRestException as e:
            logger.error(f"❌ Twilio initialization failed: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Unexpected error during Twilio initialization: {e}")
            self.client = None


    def send_otp_sms(self, mobile):
        """Send OTP via SMS using Twilio Verify"""
        try:
            if not self.client:
                return {
                    'success': False,
                    'error': 'Twilio client not initialized'
                }

            # Format mobile number for Twilio
            formatted_mobile = self._format_mobile(mobile)
            logger.info(f"🔧 Sending OTP to: {formatted_mobile}")

            # Send verification
            verification = self.client.verify \
                .v2 \
                .services(self.verify_service_sid) \
                .verifications \
                .create(to=formatted_mobile, channel='sms')

            logger.info(f"✅ OTP sent successfully! SID: {verification.sid}, Status: {verification.status}")
            
            return {
                'success': True,
                'sid': verification.sid,
                'status': verification.status,
                'formatted_mobile': formatted_mobile
            }
            
        except TwilioRestException as e:
            logger.error(f"❌ Twilio API error: {e.code} - {e.msg}")
            return {
                'success': False,
                'error': f"Twilio error: {e.msg}",
                'code': e.code
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error sending OTP: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def verify_otp(self, mobile, otp):
        """Verify OTP using Twilio Verify"""
        try:
            if not self.client:
                return {
                    'success': False,
                    'error': 'Twilio client not initialized'
                }

            formatted_mobile = self._format_mobile(mobile)
            logger.info(f"🔧 Verifying OTP for: {formatted_mobile}")

            verification_check = self.client.verify \
                .v2 \
                .services(self.verify_service_sid) \
                .verification_checks \
                .create(to=formatted_mobile, code=otp)

            is_valid = verification_check.status == 'approved'
            logger.info(f"✅ OTP verification result: {verification_check.status} (Valid: {is_valid})")

            return {
                'success': True,
                'valid': is_valid,
                'status': verification_check.status
            }
            
        except TwilioRestException as e:
            logger.error(f"❌ Twilio verification error: {e.code} - {e.msg}")
            return {
                'success': False,
                'error': f"Twilio error: {e.msg}",
                'code': e.code
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error verifying OTP: {str(e)}")
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

    def get_service_info(self):
        """Get information about the Twilio Verify service"""
        try:
            if not self.client:
                return None
                
            service = self.client.verify.v2.services(self.verify_service_sid).fetch()
            return {
                'friendly_name': service.friendly_name,
                'code_length': service.code_length,
                'lookup_enabled': service.lookup_enabled,
                'psd2_enabled': service.psd2_enabled,
                'skip_sms_to_landlines': service.skip_sms_to_landlines,
                'dtmf_input_required': service.dtmf_input_required,
                'tts_name': service.tts_name,
                'date_created': service.date_created,
                'date_updated': service.date_updated,
                'url': service.url,
            }
        except Exception as e:
            logger.error(f"❌ Error fetching service info: {e}")
            return None

# Global instance
twilio_service = TwilioService()