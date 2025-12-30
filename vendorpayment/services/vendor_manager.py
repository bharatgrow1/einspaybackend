import time
from .eko_vendor_service import EkoVendorService
from vendorpayment.models import VendorPayment
import logging

logger = logging.getLogger(__name__)

class VendorManager:
    def __init__(self):
        self.eko = EkoVendorService()

    def initiate_payment(self, data, vendor_payment_id):
        """Initiate payment with EKO API"""
        try:
            vendor_payment = VendorPayment.objects.get(id=vendor_payment_id)
            client_ref_id = vendor_payment.client_ref_id
            
            logger.info(f"🔄 Initiating EKO payment for VendorPayment {vendor_payment_id}")
            logger.info(f"🔄 Client Ref ID: {client_ref_id}")
            logger.info(f"🔄 Amount: {data.get('amount')}")

            payload = {
                "initiator_id": self.eko.INITIATOR_ID,
                "client_ref_id": client_ref_id,
                "service_code": 45,
                "payment_mode": data['payment_mode'],
                "recipient_name": data['recipient_name'],
                "account": data['account'],
                "ifsc": data['ifsc'],
                "amount": str(data['amount']),
                "source": "NEWCONNECT",
                "sender_name": "VendorService App",
            }

            logger.info(f"📤 EKO Payload: {payload}")
            
            api_res = self.eko.initiate_payment(payload)
            logger.info(f"✅ EKO Response: {api_res}")
            
            vendor_payment.eko_tid = api_res.get("data", {}).get("tid")
            vendor_payment.bank_ref_num = api_res.get("data", {}).get("bank_ref_num", "")
            vendor_payment.timestamp = api_res.get("data", {}).get("timestamp", "")
            vendor_payment.save()
            
            return api_res
            
        except Exception as e:
            logger.error(f"❌ EKO API Error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "status": 1,
                "message": f"EKO API Error: {str(e)}",
                "data": {}
            }

vendor_manager = VendorManager()