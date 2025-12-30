from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction as db_transaction
from django.utils import timezone
import logging
from users.models import Transaction
from decimal import Decimal
from .services.otp_router import otp_router
from django.conf import settings
from .models import VendorBank, VendorOTP
from .serializers import (
    VendorMobileVerificationSerializer,
    VendorOTPVerifySerializer,
    VendorBankSerializer,
    AddVendorBankSerializer,
    SearchVendorByMobileSerializer
)
from .services.mobile_verification import vendor_mobile_verifier
from .services.eko_vendor_service import bank_verifier

logger = logging.getLogger(__name__)

class VendorManagerViewSet(viewsets.ViewSet):
    """Vendor mobile and bank verification management"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def send_mobile_otp(self, request):
        """Step 1: Send OTP to vendor mobile (Twilio / MSG91)"""

        serializer = VendorMobileVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mobile = serializer.validated_data['mobile']
        user = request.user

        # 🔹 Check if already verified
        already_verified = VendorBank.objects.filter(
            user=user,
            vendor_mobile=mobile,
            is_mobile_verified=True
        ).exists()

        if already_verified:
            return Response({
                "success": True,
                "message": "Mobile already verified",
                "next_step": "add_bank_details"
            })

        # 🔹 Send OTP using OTP Router (Twilio or MSG91)
        result = otp_router.send_otp(mobile)

        if result.get("success"):
            return Response({
                "success": True,
                "message": "OTP sent successfully",
                "mobile": mobile,
                "provider": result.get("provider", settings.OTP_PROVIDER)
            })

        # 🔹 If failed
        return Response({
            "success": False,
            "error": result.get("error", "Failed to send OTP")
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    @action(detail=False, methods=['post'])
    def verify_mobile_otp(self, request):
        """Step 2: Verify OTP (Twilio / MSG91)"""

        serializer = VendorOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mobile = serializer.validated_data['mobile']
        otp = serializer.validated_data['otp']
        user = request.user

        # 🔹 Verify OTP using OTP Router
        result = otp_router.verify_otp(mobile, otp)

        if not result.get("success"):
            return Response({
                "success": False,
                "error": result.get("error", "Invalid or expired OTP")
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "message": "Mobile number verified successfully",
            "mobile": mobile,
            "verification_method": settings.OTP_PROVIDER.lower(),
            "next_step": "add_bank_details"
        })

    
    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def add_vendor_bank(self, request):
        """Add and verify bank details WITHOUT OTP - Mobile automatically considered verified"""
        serializer = AddVendorBankSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        mobile = serializer.validated_data['mobile']
        recipient_name = serializer.validated_data['recipient_name']
        account_number = serializer.validated_data['account_number']
        ifsc_code = serializer.validated_data['ifsc_code'].upper()
        
        # ✅ 1. Check wallet balance for beneficiary fee
        wallet = user.wallet
        beneficiary_fee = Decimal('2.90')
        
        if wallet.balance < beneficiary_fee:
            return Response({
                'success': False,
                'error': f'Insufficient balance. ₹{beneficiary_fee} required for beneficiary verification. Available: ₹{wallet.balance}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ 2. Check if this bank already exists for this user+mobile
        existing_bank = VendorBank.objects.filter(
            user=user,
            vendor_mobile=mobile,
            account_number=account_number
        ).first()
        
        if existing_bank:
            return Response({
                'success': False,
                'error': 'This bank account is already added for this mobile number.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ 3. Verify bank details using EKO API
        logger.info(f"🔍 Verifying bank details for vendor: {mobile}")
        verification_result = bank_verifier.verify_bank_details(
            ifsc_code=ifsc_code,
            account_number=account_number,
            mobile=mobile,
            customer_name=recipient_name
        )
        
        if not verification_result['success']:
            return Response({
                'success': False,
                'error': f"Bank verification failed: {verification_result.get('error', 'Unknown error')}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not verification_result['verified']:
            return Response({
                'success': False,
                'error': 'Bank account verification failed. Please check details.',
                'api_response': verification_result.get('data', {})
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ 4. Bank verified successfully
        bank_name = verification_result.get('bank_name', '')
        name_match = verification_result.get('name_match', False)
        
        if not name_match:
            return Response({
                'success': False,
                'error': 'Account holder name does not match. Please check the name.',
                'expected_name': verification_result.get('account_holder_name'),
                'provided_name': recipient_name
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ 5. Deduct beneficiary fee from wallet WITHOUT PIN
        try:
            # Use new method that doesn't require PIN
            deducted_amount = wallet.deduct_fee_without_pin(beneficiary_fee)
            
            # Create transaction record for fee deduction
            Transaction.objects.create(
                wallet=wallet,
                amount=Decimal('0.00'),
                service_charge=deducted_amount,
                net_amount=Decimal('0.00'),
                transaction_type='debit',
                transaction_category='beneficiary_verification',
                description=f"Beneficiary verification fee for {recipient_name} - {account_number[-4:]}",
                created_by=user,
                status='success',
                metadata={
                    'vendor_mobile': mobile,
                    'recipient_name': recipient_name,
                    'account_number': account_number[-4:],
                    'ifsc_code': ifsc_code,
                    'bank_name': bank_name,
                    'fee_type': 'beneficiary_verification'
                }
            )
            
            logger.info(f"✅ Beneficiary fee deducted (without PIN): ₹{deducted_amount} from {user.username}")
            
        except ValueError as e:
            return Response({
                'success': False,
                'error': f'Failed to deduct beneficiary fee: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ 6. Create VendorBank record with BOTH verified
        vendor_bank = VendorBank.objects.create(
            user=user,
            vendor_mobile=mobile,
            recipient_name=recipient_name,
            account_number=account_number,
            ifsc_code=ifsc_code,
            bank_name=bank_name,
            is_mobile_verified=True,
            is_bank_verified=True,
            beneficiary_fee=beneficiary_fee,
            verification_ref_id=verification_result.get('data', {}).get('tid', '')
        )
        
        logger.info(f"✅ Vendor bank added successfully (BOTH mobile and bank verified): {vendor_bank}")
        
        return Response({
            'success': True,
            'message': f'Bank account verified and added successfully. ₹{beneficiary_fee} deducted as verification fee.',
            'vendor_bank': VendorBankSerializer(vendor_bank).data,
            'fee_deducted': float(beneficiary_fee),
            'remaining_balance': float(wallet.balance)
        })
    
    @action(detail=False, methods=['post'])
    def search_vendor_by_mobile(self, request):
        """Search vendor banks by mobile number - Show ALL banks"""
        serializer = SearchVendorByMobileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mobile = serializer.validated_data['mobile']
        user = request.user
        
        # Get ALL banks for this mobile number (any status)
        vendor_banks = VendorBank.objects.filter(
            user=user,
            vendor_mobile=mobile
        ).order_by('-created_at')
        
        if not vendor_banks.exists():
            return Response({
                'success': True,
                'message': 'No banks found for this mobile number',
                'banks': [],
                'mobile': mobile
            })
        
        serializer = VendorBankSerializer(vendor_banks, many=True)
        
        return Response({
            'success': True,
            'message': f'Found {vendor_banks.count()} bank(s) for this mobile',
            'mobile': mobile,
            'banks': serializer.data
        })
    


    @action(detail=False, methods=['post'])
    def get_verified_banks(self, request):
        """Get only verified banks for mobile number"""
        serializer = SearchVendorByMobileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mobile = serializer.validated_data['mobile']
        user = request.user
        
        # Get only FULLY verified banks
        vendor_banks = VendorBank.objects.filter(
            user=user,
            vendor_mobile=mobile,
            is_mobile_verified=True,
            is_bank_verified=True
        ).order_by('-created_at')
        
        serializer = VendorBankSerializer(vendor_banks, many=True)
        
        return Response({
            'success': True,
            'message': f'Found {vendor_banks.count()} verified bank(s) for this mobile',
            'mobile': mobile,
            'banks': serializer.data,
            'verification_status': 'fully_verified'
        })


    @action(detail=False, methods=['get'])
    def my_vendor_banks(self, request):
        """Get all vendor banks for current user"""
        user = request.user
        vendor_banks = VendorBank.objects.filter(user=user).order_by('-created_at')
        
        serializer = VendorBankSerializer(vendor_banks, many=True)
        
        return Response({
            'success': True,
            'count': vendor_banks.count(),
            'banks': serializer.data
        })
    
    @action(detail=True, methods=['delete'])
    def remove_vendor_bank(self, request, pk=None):
        """Remove a vendor bank"""
        try:
            vendor_bank = VendorBank.objects.get(id=pk, user=request.user)
            
            # Check if this bank is used in any payments
            from .models import VendorPayment
            payments_count = VendorPayment.objects.filter(
                recipient_account=vendor_bank.account_number,
                user=request.user
            ).count()
            
            if payments_count > 0:
                return Response({
                    'success': False,
                    'error': f'Cannot delete. This bank is used in {payments_count} payment(s).'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            vendor_bank.delete()
            
            return Response({
                'success': True,
                'message': 'Vendor bank removed successfully'
            })
            
        except VendorBank.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Vendor bank not found'
            }, status=status.HTTP_404_NOT_FOUND)
