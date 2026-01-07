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
    SearchVendorByMobileSerializer, VerifyVendorBankSerializer
)
from .services.mobile_verification import vendor_mobile_verifier
from .services.eko_vendor_service import bank_verifier

logger = logging.getLogger(__name__)

class VendorManagerViewSet(viewsets.ViewSet):
    """Vendor mobile and bank verification management"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def send_mobile_otp(self, request):
        serializer = VendorMobileVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mobile = serializer.validated_data['mobile']
        vendor_name = serializer.validated_data['vendor_name']
        user = request.user

        # ✅ Check OTP table instead of VendorBank
        otp_record = VendorOTP.objects.filter(
            vendor_mobile=mobile,
            is_verified=True
        ).first()

        if otp_record:
            return Response({
                "success": True,
                "message": "Mobile already verified",
                "mobile": mobile,
                "vendor_name": otp_record.vendor_name,
                "next_step": "add_bank_details"
            })

        result = otp_router.send_otp(mobile)

        if result.get("success"):
            VendorOTP.objects.update_or_create(
                vendor_mobile=mobile,
                defaults={
                    "vendor_name": vendor_name,
                    "is_verified": False,
                    "expires_at": timezone.now() + timezone.timedelta(minutes=10)
                }
            )

            return Response({
                "success": True,
                "message": "OTP sent successfully",
                "mobile": mobile
            })

        return Response({
            "success": False,
            "error": "Failed to send OTP"
        }, status=500)


    
    @action(detail=False, methods=['post'])
    def verify_mobile_otp(self, request):
        serializer = VendorOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mobile = serializer.validated_data['mobile']
        otp = serializer.validated_data['otp']

        record = VendorOTP.objects.filter(
            vendor_mobile=mobile,
            otp=otp,
            is_verified=False
        ).first()

        if not record or record.is_expired():
            return Response({
                "success": False,
                "error": "Invalid or expired OTP"
            }, status=400)

        record.is_verified = True
        record.save()

        return Response({
            "success": True,
            "message": "Mobile verified permanently",
            "mobile": mobile,
            "vendor_name": record.vendor_name,
            "next_step": "add_bank_details"
        })

    
    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def add_vendor_bank(self, request):

        serializer = AddVendorBankSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        vendor_mobile = serializer.validated_data['mobile']
        recipient_name = serializer.validated_data['recipient_name']
        account_number = serializer.validated_data['account_number']
        ifsc_code = serializer.validated_data['ifsc_code'].upper()

        retailer_mobile = user.phone_number
        if not retailer_mobile:
            return Response({
                'success': False,
                'error': 'Your mobile number is not found. Please update profile.'
            }, status=status.HTTP_400_BAD_REQUEST)

        logger.info(
            f"➕ Adding vendor bank | Retailer={retailer_mobile} | "
            f"Vendor={vendor_mobile} | Account=****{account_number[-4:]}"
        )

        # 🔒 Duplicate bank protection
        existing_bank = VendorBank.objects.filter(
            user=user,
            vendor_mobile=vendor_mobile,
            account_number=account_number
        ).first()

        if existing_bank:
            return Response({
                'success': False,
                'error': 'This bank account is already added for this mobile number.'
            }, status=status.HTTP_400_BAD_REQUEST)

        is_verified = serializer.validated_data.get("is_verified", False)
        
        vendor_bank = VendorBank.objects.create(
            user=user,
            vendor_mobile=vendor_mobile,
            recipient_name=recipient_name,
            account_number=account_number,
            ifsc_code=ifsc_code,
            bank_name=request.data.get('bank_name', ''),
            is_mobile_verified=True,
            is_bank_verified=is_verified,
        )

        logger.info(
            f"✅ Vendor bank added successfully | ID={vendor_bank.id} | "
            f"User={user.username}"
        )

        return Response({
            'success': True,
            'message': 'Bank account added successfully',
            'vendor_bank': VendorBankSerializer(vendor_bank).data
        }, status=status.HTTP_201_CREATED)

    
    @action(detail=False, methods=['post'])
    def search_vendor_by_mobile(self, request):
        """Search vendor banks by mobile number - Show ALL banks"""
        serializer = SearchVendorByMobileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mobile = serializer.validated_data['mobile']
        user = request.user
        
        vendor_banks = VendorBank.objects.filter(
            # user=user,
            vendor_mobile=mobile
        ).order_by('-created_at')


        otp_record = VendorOTP.objects.filter(
            vendor_mobile=mobile,
            is_verified=True
        ).first()
        vendor_name = otp_record.vendor_name if otp_record else ""
        
        if not vendor_banks.exists():
            return Response({
                'success': True,
                'message': 'No banks found for this mobile number',
                'vendor_name': vendor_name,
                'banks': [],
                'mobile': mobile
            })
        
        serializer = VendorBankSerializer(vendor_banks, many=True)
        
        return Response({
            'success': True,
            'message': f'Found {vendor_banks.count()} bank(s) for this mobile',
            'vendor_name': vendor_name,
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
        
        vendor_banks = VendorBank.objects.filter(
            # user=user,
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


    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def verify_bank(self, request):

        serializer = VerifyVendorBankSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        wallet = user.wallet

        vendor_mobile = serializer.validated_data['mobile']
        account_number = serializer.validated_data['account_number']

        from dmt.models import EkoBank
        data = serializer.validated_data

        if data.get("ifsc_code"):
            ifsc_code = data["ifsc_code"].upper()
        else:
            bank_code = data["bank_code"].upper()
            bank = EkoBank.objects.filter(
                bank_code=bank_code,
                static_ifsc__isnull=False
            ).first()

            if not bank:
                return Response({
                    "success": False,
                    "error": "Invalid bank code or IFSC not available"
                }, status=400)

            ifsc_code = bank.static_ifsc

        existing_bank = VendorBank.objects.filter(
            # user=user,
            vendor_mobile=vendor_mobile,
            account_number=account_number,
            is_bank_verified=True
        ).first()

        if existing_bank:
            return Response({
                "success": True,
                "already_verified": True,
                "message": "Account already added & verified. No charges applied.",
                "recipient_name": existing_bank.recipient_name,
                "bank_name": existing_bank.bank_name,
                "fee_deducted": 0,
                "remaining_balance": float(wallet.balance)
            })

        # 🔍 pending bank
        pending_bank = VendorBank.objects.filter(
            # user=user,
            vendor_mobile=vendor_mobile,
            account_number=account_number,
            is_bank_verified=False
        ).first()

        beneficiary_fee = Decimal("3.0")

        if wallet.balance < beneficiary_fee:
            return Response({
                "success": False,
                "error": "Insufficient balance"
            }, status=400)

        verification_result = bank_verifier.verify_bank_details(
            ifsc_code=ifsc_code,
            account_number=account_number,
            retailer_mobile=user.phone_number,
            customer_name=""
        )

        if not verification_result.get("success") or not verification_result.get("verified"):
            return Response({
                "success": False,
                "error": "Bank verification failed"
            }, status=400)

        deducted = wallet.deduct_fee_without_pin(beneficiary_fee)

        Transaction.objects.create(
            wallet=wallet,
            amount=deducted,
            service_charge=Decimal("0.00"),
            net_amount=deducted,
            transaction_type="debit",
            transaction_category="beneficiary_verification",
            description=f"Bank verification fee for ****{account_number[-4:]}",
            created_by=user,
            status="success",
        )

        # ✅ IMPORTANT FIX
        if pending_bank:
            pending_bank.is_bank_verified = True
            pending_bank.save(update_fields=["is_bank_verified"])

        return Response({
            "success": True,
            "verified": True,
            "recipient_name": verification_result.get("account_holder_name"),
            "bank_name": verification_result.get("bank_name"),
            "fee_deducted": float(beneficiary_fee),
            "remaining_balance": float(wallet.balance)
        })
