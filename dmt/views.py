from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import logging
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.db import models
from rest_framework.permissions import IsAdminUser
from dmt.permissions import IsSuperAdmin



from .services.dmt_manager import dmt_manager
from .serializers import (
    DMTOnboardSerializer, DMTGetProfileSerializer, DMTBiometricKycSerializer,
    DMTKycOTPVerifySerializer, DMTAddRecipientSerializer, DMTGetRecipientsSerializer,
    DMTSendTxnOTPSerializer, DMTInitiateTransactionSerializer, DMTCreateCustomerSerializer,
    DMTVerifyCustomerSerializer, DMTResendOTPSerializer, EkoBankSerializer, 
    DMTTransactionInquirySerializer, DMTRefundSerializer, DMTRefundOTPResendSerializer, 
    DMTWalletTransactionSerializer, DMTPlanSerializer, EKOChargeConfigSerializer, DMTChargeSchemeSerializer,
    DMTChargeSchemeCreateSerializer, ChargePreviewSerializer
)

from .models import EkoBank, DMTTransaction, DMTPlan, EKOChargeConfig, DMTChargeScheme

logger = logging.getLogger(__name__)

class DMTOnboardViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def onboard_user(self, request):
        """
        User Onboarding
        POST /api/dmt/onboard/onboard_user/
        """
        serializer = DMTOnboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.onboard_user(serializer.validated_data)
        return Response(response)
    


class DMTCustomerVerificationViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def verify_customer(self, request):
        """
        Verify Customer with OTP
        POST /api/dmt/verification/verify_customer/
        """
        try:
            serializer = DMTVerifyCustomerSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            response = dmt_manager.verify_customer_identity(
                serializer.validated_data['customer_mobile'],
                serializer.validated_data['otp'],
                serializer.validated_data['otp_ref_id']
            )
            
            return Response(response)
            
        except Exception as e:
            logger.error(f"Verify customer error: {str(e)}")
            return Response({
                "status": 1,
                "message": f"Failed to verify customer: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def resend_otp(self, request):
        """
        Resend OTP for verification
        POST /api/dmt/verification/resend_otp/
        """
        try:
            serializer = DMTResendOTPSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            response = dmt_manager.resend_otp(
                serializer.validated_data['customer_mobile']
            )
            
            return Response(response)
            
        except Exception as e:
            logger.error(f"Resend OTP error: {str(e)}")
            return Response({
                "status": 1,
                "message": f"Failed to resend OTP: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


class DMTCustomerViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def create_customer(self, request):
        """
        Create Customer for DMT
        POST /api/dmt/customer/create_customer/
        
        Call this when Get Sender Profile returns "Customer Not Enrolled"
        """
        try:
            serializer = DMTCreateCustomerSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            response = dmt_manager.create_customer(serializer.validated_data)
            
            return Response(response)
            
        except Exception as e:
            logger.error(f"Create customer error: {str(e)}")
            return Response({
                "status": 1,
                "message": f"Failed to create customer: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class DMTProfileViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def get_sender_profile(self, request):
        """
        Get Sender Profile
        POST /api/dmt/profile/get_sender_profile/
        """
        serializer = DMTGetProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.get_sender_profile(
            serializer.validated_data['customer_mobile']
        )
        return Response(response)

class DMTKYCViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=True, methods=['post'], url_path='biometric_kyc')
    def biometric_kyc(self, request, pk=None):
        """
        POST /api/dmt/kyc/<customer_id>/biometric_kyc/
        """
        aadhar = request.data.get("aadhar")
        piddata = request.data.get("piddata")

        if not aadhar or not piddata:
            return Response({
                "status": 0,
                "message": "Missing Data"
            }, status=status.HTTP_400_BAD_REQUEST)

        response = dmt_manager.customer_ekyc_biometric(
            pk,
            aadhar,
            piddata
        )

        return Response(response)
    
    @action(detail=False, methods=['post'])
    def verify_kyc_otp(self, request):
        """
        Verify KYC OTP
        POST /api/dmt/kyc/verify_kyc_otp/
        """
        serializer = DMTKycOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.verify_ekyc_otp(
            serializer.validated_data['customer_id'],
            serializer.validated_data['otp'],
            serializer.validated_data['otp_ref_id'],
            serializer.validated_data['kyc_request_id']
        )
        return Response(response)

class DMTRecipientViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def add_recipient(self, request):
        """
        Add Recipient
        POST /api/dmt/recipient/add_recipient/
        """
        serializer = DMTAddRecipientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.add_recipient(
            customer_id=serializer.validated_data['customer_id'],
            recipient_data=serializer.validated_data,
            user=request.user 
        )
        return Response(response)
    
    @action(detail=False, methods=['post'])
    def get_recipient_list(self, request):
        """
        Get Recipient List
        POST /api/dmt/recipient/get_recipient_list/
        """
        serializer = DMTGetRecipientsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.get_recipient_list(
            serializer.validated_data['customer_id']
        )
        return Response(response)

class DMTTransactionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def initiate_with_wallet(self, request):
        """
        Initiate DMT transaction with wallet payment
        POST /api/dmt/transaction/initiate_with_wallet/
        """
        try:
            serializer = DMTWalletTransactionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            user = request.user
            
            result = dmt_manager.initiate_transaction_with_wallet(
                user=user,
                transaction_data=serializer.validated_data
            )
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"DMT wallet payment error: {str(e)}")
            return Response({
                "status": 1,
                "message": f"Failed to process DMT payment: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    
    @action(detail=False, methods=['post'])
    def send_transaction_otp(self, request):
        """
        Send Transaction OTP
        POST /api/dmt/transaction/send_transaction_otp/
        """
        serializer = DMTSendTxnOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.send_transaction_otp(
            serializer.validated_data['customer_id'],
            serializer.validated_data['recipient_id'],
            serializer.validated_data['amount']
        )
        return Response(response)
    
    @action(detail=False, methods=['post'])
    def initiate_transaction(self, request):
        """
        Initiate Transaction
        POST /api/dmt/transaction/initiate_transaction/
        """
        serializer = DMTInitiateTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.initiate_transaction(
            serializer.validated_data['customer_id'],
            serializer.validated_data['recipient_id'],
            serializer.validated_data['amount'],
            serializer.validated_data['otp'],
            serializer.validated_data['otp_ref_id']
        )
        return Response(response)
    


    @staticmethod
    def get_all_child_users(user):
        """Simple hierarchy logic - same as vendor"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        role = user.role

        if role == "superadmin":
            return User.objects.all()
        elif role == "admin":
            return User.objects.filter(
                Q(created_by=user) |
                Q(created_by__created_by=user) |
                Q(created_by__created_by__created_by=user) |
                Q(id=user.id)
            )
        elif role == "master":
            return User.objects.filter(
                Q(created_by=user) |
                Q(created_by__created_by=user) |
                Q(id=user.id)
            )
        elif role == "dealer":
            return User.objects.filter(
                Q(created_by=user) |
                Q(id=user.id)
            )
        else:
            return User.objects.filter(id=user.id)
    
    @action(detail=False, methods=['get'])
    def report(self, request):
        """
        Simple DMT Report - Everyone sees their hierarchy
        GET /api/dmt/transaction/report/?status=success&start_date=2024-01-01
        """
        try:
            allowed_users = self.get_all_child_users(request.user)
            
            queryset = DMTTransaction.objects.filter(
                user__in=allowed_users
            ).order_by('-initiated_at')
            
            status = request.GET.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            if start_date:
                queryset = queryset.filter(initiated_at__date__gte=start_date)
            if end_date:
                queryset = queryset.filter(initiated_at__date__lte=end_date)
            
            search = request.GET.get('search')
            if search:
                queryset = queryset.filter(
                    Q(recipient_name__icontains=search) |
                    Q(recipient_account__icontains=search) |
                    Q(eko_tid__icontains=search)
                )
            
            paginator = PageNumberPagination()
            paginator.page_size = 20
            page = paginator.paginate_queryset(queryset, request)
            
            data = []
            for txn in page:
                data.append({
                    'id': txn.id,
                    'transaction_id': txn.transaction_id,
                    'date': txn.initiated_at.strftime('%d-%m-%Y %H:%M'),
                    'user': txn.user.username,
                    'recipient_name': txn.recipient_name,
                    'account': f"****{txn.recipient_account[-4:]}" if txn.recipient_account else "",
                    'ifsc': txn.recipient_ifsc,
                    'amount': str(txn.amount),
                    'status': txn.status,
                    'eko_tid': txn.eko_tid,
                    'client_ref_id': txn.client_ref_id,
                    'bank_ref': txn.eko_bank_ref_num,
                    'sender_mobile': txn.sender_mobile
                })
            
            return paginator.get_paginated_response({
                'status': 0,
                'data': data
            })
            
        except Exception as e:
            logger.error(f"DMT report error: {str(e)}")
            return Response({
                'status': 1,
                'message': str(e)
            }, status=400)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Simple Summary for dashboard
        GET /api/dmt/transaction/summary/
        """
        try:
            allowed_users = self.get_all_child_users(request.user)
            
            queryset = DMTTransaction.objects.filter(user__in=allowed_users)
            
            today = timezone.now().date()
            today_qs = queryset.filter(initiated_at__date=today)
            
            summary = {
                'total_count': queryset.count(),
                'total_amount': float(queryset.aggregate(
                    total=models.Sum('amount')
                )['total'] or 0),
                'today_count': today_qs.count(),
                'today_amount': float(today_qs.aggregate(
                    total=models.Sum('amount')
                )['total'] or 0),
                'success_count': queryset.filter(status='success').count(),
                'failed_count': queryset.filter(status='failed').count(),
                'pending_count': queryset.filter(status__in=['initiated', 'processing']).count(),
            }
            
            return Response({
                'status': 0,
                'data': summary
            })
            
        except Exception as e:
            logger.error(f"DMT summary error: {str(e)}")
            return Response({
                'status': 1,
                'message': str(e)
            }, status=400)
    

class BankViewSet(viewsets.ModelViewSet):
    queryset = EkoBank.objects.all().order_by("bank_name")
    serializer_class = EkoBankSerializer
    lookup_field = "bank_id"

    filter_backends = [filters.SearchFilter]
    search_fields = ['bank_name', 'bank_code']



class DMTTransactionInquiryViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def check_status(self, request):

        try:
            serializer = DMTTransactionInquirySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            response = dmt_manager.transaction_inquiry(
                serializer.validated_data['inquiry_id'],
                serializer.validated_data.get('is_client_ref_id', False)
            )
            
            return Response(response)
            
        except Exception as e:
            logger.error(f"Transaction inquiry error: {str(e)}")
            return Response({
                "status": 1,
                "message": f"Failed to check transaction status: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class DMTRefundViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def refund(self, request):
        """Refund Payment"""
        serializer = DMTRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tid = serializer.validated_data['tid']
        otp = serializer.validated_data['otp']
        
        response = dmt_manager.refund_transaction(tid, otp)
        return Response(response)

    @action(detail=False, methods=['post'])
    def resend_otp(self, request):
        """
        Resend Refund OTP
        POST /api/dmt/refund/resend_otp/
        """
        serializer = DMTRefundOTPResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tid = serializer.validated_data['tid']

        response = dmt_manager.resend_refund_otp(tid)

        return Response(response)  
    

class DMTChargeAdminViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['create_plan', 'create_charge_scheme', 'activate_scheme']:
            return [IsSuperAdmin()]
        return [IsAdminUser()]
    
    @action(detail=False, methods=['get'])
    def plans(self, request):
        """Get all DMT plans"""
        plans = DMTPlan.objects.filter(is_active=True)
        serializer = DMTPlanSerializer(plans, many=True)
        return Response({
            'status': 0,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def create_plan(self, request):
        """Create new plan (superadmin only)"""
        serializer = DMTPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        
        return Response({
            'status': 0,
            'message': 'Plan created successfully',
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def eko_charges(self, request):
        """Get all EKO charges (for dropdown)"""
        charges = EKOChargeConfig.objects.all()
        
        ranges = []
        for charge in charges:
            ranges.append({
                'id': charge.id,
                'amount_from': str(charge.amount_from),
                'amount_to': str(charge.amount_to),
                'display': f"₹{charge.amount_from} - ₹{charge.amount_to}",
                'eko_commission': str(charge.commission_after_tds)
            })
        
        return Response({
            'status': 0,
            'data': ranges
        })
    
    @action(detail=False, methods=['get'])
    def eko_charge_detail(self, request):
        """Get EKO charge for specific amount range"""
        amount_from = request.GET.get('amount_from')
        amount_to = request.GET.get('amount_to')
        
        if not amount_from or not amount_to:
            return Response({
                'status': 1,
                'message': 'amount_from and amount_to are required'
            }, status=400)
        
        try:
            charge = EKOChargeConfig.objects.get(
                amount_from=amount_from,
                amount_to=amount_to
            )
            serializer = EKOChargeConfigSerializer(charge)
            return Response({
                'status': 0,
                'data': serializer.data
            })
        except EKOChargeConfig.DoesNotExist:
            return Response({
                'status': 1,
                'message': 'Charge not found for this range'
            }, status=404)
    
    @action(detail=False, methods=['get'])
    def charge_schemes(self, request):
        """Get all charge schemes"""
        schemes = DMTChargeScheme.objects.select_related('plan').all()
        serializer = DMTChargeSchemeSerializer(schemes, many=True)
        return Response({
            'status': 0,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def create_charge_scheme(self, request):
        """Create new charge scheme (superadmin only)"""
        serializer = DMTChargeSchemeCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Get EKO commission for the amount range
                amount_from = serializer.validated_data['amount_from']
                amount_to = serializer.validated_data['amount_to']
                
                eko_charge = EKOChargeConfig.objects.get(
                    amount_from=amount_from,
                    amount_to=amount_to
                )
                
                # Create scheme with eko_commission
                scheme = DMTChargeScheme.objects.create(
                    name=serializer.validated_data['name'],
                    plan=serializer.validated_data['plan'],
                    amount_range=f"{amount_from}-{amount_to}",
                    amount_from=amount_from,
                    amount_to=amount_to,
                    eko_commission=eko_charge.commission_after_tds,
                    charge_type=serializer.validated_data['charge_type'],
                    percentage_charge=serializer.validated_data.get('percentage_charge', 0),
                    flat_charge=serializer.validated_data.get('flat_charge', 0),
                    retailer_percentage=serializer.validated_data['retailer_percentage'],
                    dealer_percentage=serializer.validated_data['dealer_percentage'],
                    master_percentage=serializer.validated_data['master_percentage'],
                    admin_percentage=serializer.validated_data['admin_percentage'],
                    superadmin_percentage=serializer.validated_data['superadmin_percentage'],
                    is_active=True
                )
                
                return Response({
                    'status': 0,
                    'message': 'Charge scheme created successfully',
                    'data': DMTChargeSchemeSerializer(scheme).data
                })
                
            except EKOChargeConfig.DoesNotExist:
                return Response({
                    'status': 1,
                    'message': 'EKO charges not found for this amount range'
                }, status=400)
            except Exception as e:
                return Response({
                    'status': 1,
                    'message': str(e)
                }, status=400)
        else:
            return Response({
                'status': 1,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=400)
    
    @action(detail=True, methods=['post'])
    def activate_scheme(self, request, pk=None):
        """Activate a scheme (deactivate others for same plan)"""
        try:
            scheme = DMTChargeScheme.objects.get(pk=pk)
            
            DMTChargeScheme.objects.filter(
                plan=scheme.plan,
                amount_from=scheme.amount_from,
                amount_to=scheme.amount_to
            ).update(is_active=False)
            
            scheme.is_active = True
            scheme.save()
            
            return Response({
                'status': 0,
                'message': f'Scheme activated successfully'
            })
            
        except DMTChargeScheme.DoesNotExist:
            return Response({
                'status': 1,
                'message': 'Scheme not found'
            }, status=404)
    
    @action(detail=False, methods=['post'])
    def preview_charge(self, request):
        """Preview charges for an amount"""
        serializer = ChargePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        schemes = serializer.validated_data['schemes']
        
        previews = []
        
        for scheme in schemes:
            distribution = scheme.calculate_charges(amount)
            
            previews.append({
                'scheme_id': scheme.id,
                'scheme_name': scheme.name,
                'plan': scheme.plan.name,
                'amount': str(amount),
                'charges': {
                    'eko_commission': str(distribution['eko_commission']),
                    'superadmin_extra': str(distribution['superadmin_extra']),
                    'total_charges': str(distribution['total_charges']),
                    'net_amount_for_retailer': str(amount - distribution['total_charges'])
                },
                'distribution': {
                    'retailer': {
                        'percentage': str(scheme.retailer_percentage),
                        'amount': str(distribution['retailer_amount'])
                    },
                    'dealer': {
                        'percentage': str(scheme.dealer_percentage),
                        'amount': str(distribution['dealer_amount'])
                    },
                    'master': {
                        'percentage': str(scheme.master_percentage),
                        'amount': str(distribution['master_amount'])
                    },
                    'admin': {
                        'percentage': str(scheme.admin_percentage),
                        'amount': str(distribution['admin_amount'])
                    },
                    'superadmin': {
                        'percentage': str(scheme.superadmin_percentage),
                        'amount': str(distribution['superadmin_amount'])
                    }
                }
            })
        
        return Response({
            'status': 0,
            'data': {
                'amount': str(amount),
                'previews': previews
            }
        })
    
    @action(detail=False, methods=['get'])
    def available_ranges(self, request):
        """Get all available amount ranges for dropdown"""
        ranges = EKOChargeConfig.objects.values('amount_from', 'amount_to').distinct()
        
        data = []
        for r in ranges:
            data.append({
                'value': f"{r['amount_from']}-{r['amount_to']}",
                'display': f"₹{r['amount_from']} - ₹{r['amount_to']}",
                'amount_from': str(r['amount_from']),
                'amount_to': str(r['amount_to'])
            })
        
        return Response({
            'status': 0,
            'data': data
        })