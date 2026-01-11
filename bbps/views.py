from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.db import transaction as db_transaction
from django.utils import timezone
import logging
from decimal import Decimal
from users.models import Transaction
from django.db.models import Q
# from users.models import User
from django.contrib.auth import get_user_model
from .models import bbpsTransaction, Operator, Plan, bbpsServiceCharge
from .serializers import (
    bbpsTransactionSerializer, OperatorSerializer, PlanSerializer,
    bbpsRequestSerializer, BillFetchRequestSerializer,
    EKOOperatorResponseSerializer, EKOBillFetchResponseSerializer,
    EKObbpsResponseSerializer
)
from .services.eko_service import bbps_manager

logger = logging.getLogger(__name__)

User = get_user_model()

class bbpsViewSet(viewsets.ViewSet):
    """bbps API endpoints"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def fetch_operators(self, request):
        """
        Fetch operators by category
        POST /api/bbps/fetch_operators/
        {
            "category": "prepaid"  # prepaid, postpaid, dth, electricity, etc.
        }
        """
        category = request.data.get('category', 'prepaid')
        
        result = bbps_manager.get_operators(category)
        
        if result['success']:
            return Response({
                'success': True,
                'category': category,
                'operators': result['operators']
            })
        
        return Response({
            'success': False,
            'message': result['message'],
            'data': result.get('data')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def operator_locations(self, request):
        """
        Fetch operator locations
        GET /api/bbps/operator_locations/
        """
        result = bbps_manager.get_operator_locations()
        
        if result['success']:
            return Response({
                'success': True,
                'locations': result['locations']
            })
        
        return Response({
            'success': False,
            'message': result['message']
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def fetch_bill(self, request):
        """
        Fetch bill details (for postpaid/utility)
        POST /api/bbps/fetch_bill/
        {
            "operator_id": "operator_id",
            "mobile_no": "9876543210",
            "utility_acc_no": "consumer_number",  # optional
            "sender_name": "Customer Name"
        }
        """
        serializer = BillFetchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        result = bbps_manager.fetch_bill_details(
            operator_id=data['operator_id'],
            mobile=data['mobile_no'],
            account_no=data.get('utility_acc_no'),
            sender_name=data.get('sender_name', 'Customer')
        )
        
        response_serializer = EKOBillFetchResponseSerializer(result)
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['post'])
    def check_balance(self, request):
        """
        Check if user has sufficient balance for bbps
        POST /api/bbps/check_balance/
        {
            "amount": 100.00,
            "pin": "1234"
        }
        """
        amount = request.data.get('amount')
        pin = request.data.get('pin')
        
        if not amount or not pin:
            return Response({
                'success': False,
                'message': 'Amount and PIN are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            wallet = request.user.wallet
            service_charge = bbpsServiceCharge.calculate_charge(Decimal(amount))
            total_amount = Decimal(amount) + service_charge
            
            if not wallet.verify_pin(pin):
                return Response({
                    'success': False,
                    'message': 'Invalid PIN'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            has_balance = wallet.has_sufficient_balance(Decimal(amount), service_charge)
            
            return Response({
                'success': True,
                'has_sufficient_balance': has_balance,
                'current_balance': wallet.balance,
                'bbps_amount': amount,
                'service_charge': service_charge,
                'total_amount': total_amount,
                'remaining_balance': wallet.balance - total_amount if has_balance else 0
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f"Error checking balance: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def bbps(self, request):
        serializer = bbpsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user = request.user
        pin = request.data.get('pin')
        
        try:
            service_charge = bbpsServiceCharge.calculate_charge(data['amount'])
            service_charge = Decimal('0.00')
            total_amount = data['amount'] + service_charge
            
            wallet = user.wallet
            
            if not pin:
                return Response({
                    'success': False,
                    'message': 'Wallet PIN is required for bbps'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not wallet.verify_pin(pin):
                return Response({
                    'success': False,
                    'message': 'Invalid wallet PIN'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not wallet.has_sufficient_balance(data['amount'], service_charge):
                return Response({
                    'success': False,
                    'message': 'Insufficient wallet balance'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            bbps_txn = bbpsTransaction.objects.create(
                user=user,
                operator_id=data['operator_id'],
                operator_type=data['operator_type'],
                circle=data.get('circle'),
                mobile_number=data['mobile'],
                consumer_number=data.get('consumer_number'),
                customer_name=data.get('customer_name'),
                amount=data['amount'],
                service_charge=service_charge,
                total_amount=total_amount,
                client_ref_id=f"RECH{int(timezone.now().timestamp())}",
                is_plan_bbps=data.get('is_plan_bbps', False),
                plan_details={
                    'plan_id': data.get('plan_id')
                } if data.get('plan_id') else None,
                status='processing',
                payment_status='processing'
            )
            
            try:
                total_deducted = wallet.deduct_amount(data['amount'], service_charge, pin)
                
                wallet_transaction = Transaction.objects.create(
                    wallet=wallet,
                    amount=data['amount'],
                    service_charge=service_charge,
                    net_amount=data['amount'],
                    transaction_type='debit',
                    transaction_category='bbps',
                    description=f"bbps for {data['mobile']} - {bbps_txn.transaction_id}",
                    created_by=user,
                    status='success'
                )
                
                logger.info(f"✅ Wallet deduction successful: ₹{total_deducted} from {user.username}")
                
            except ValueError as e:
                bbps_txn.status = 'failed'
                bbps_txn.payment_status = 'failed'
                bbps_txn.status_message = f"Payment failed: {str(e)}"
                bbps_txn.save()
                return Response({
                    'success': False,
                    'message': f"Payment failed: {str(e)}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = bbps_manager.perform_bbps(
                mobile=data['mobile'],
                amount=data['amount'],
                operator_id=data['operator_id'],
                user=user,
                circle=data.get('circle')
            )
            
            bbps_txn.eko_message = result.get('eko_message')
            bbps_txn.eko_txstatus_desc = result.get('txstatus_desc')
            bbps_txn.eko_response_status = result.get('response_status')
            bbps_txn.api_response = result.get('eko_response')


            message = ""
            
            if result['success']:
                bbps_txn.status = 'success'
                bbps_txn.payment_status = 'paid'
                
                if wallet_transaction and result.get('eko_transaction_ref'):
                    wallet_transaction.eko_tid = result.get('eko_transaction_ref')
                    wallet_transaction.save()
                
                try:
                    from commission.views import CommissionManager
                    
                    success, comm_message = CommissionManager.process_operator_commission(
                        bbps_txn=bbps_txn, 
                        wallet_transaction=wallet_transaction,
                        operator_id=data['operator_id']
                    )
                    
                    if success:
                        logger.info(f"✅ Operator commission processed for bbps: {bbps_txn.transaction_id}")
                        bbps_txn.status_message = f"bbps successful. {comm_message}"
                    else:
                        logger.warning(f"⚠️ Operator commission processing failed: {comm_message}")
                        
                except ImportError as e:
                    logger.warning(f"Commission app not available: {str(e)}")
                except Exception as e:
                    logger.error(f"❌ Commission processing error: {str(e)}")
                    import traceback
                    logger.error(f"Stack trace: {traceback.format_exc()}")
            
                
            else:
                bbps_txn.status = 'failed'
                bbps_txn.payment_status = 'failed'
                bbps_txn.status_message = result.get('message', 'bbps failed')
                bbps_txn.completed_at = timezone.now()
                
                # Refund amount if bbps failed
                try:
                    wallet.add_amount(data['amount'])
                    Transaction.objects.create(
                        wallet=wallet,
                        amount=data['amount'],
                        transaction_type='credit',
                        transaction_category='refund',
                        description=f"Refund for failed bbps {bbps_txn.transaction_id}",
                        created_by=user,
                        status='success'
                    )
                    message = f"bbps failed. Amount refunded: ₹{data['amount']}"
                except Exception as e:
                    message = f"bbps failed. Please contact support for refund: {str(e)}"
            
            bbps_txn.save()
            
            # Serialize response
            txn_serializer = bbpsTransactionSerializer(bbps_txn)
            
            return Response({
                'success': result['success'],
                'message': message,
                'transaction': txn_serializer.data,
                'wallet_balance': wallet.balance,
                'eko_response': result.get('eko_response', {})
            })
            
        except Exception as e:
            logger.error(f"bbps error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f"bbps failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def transaction_history(self, request):
        """
        Get user's bbps history
        GET /api/bbps/transaction_history/
        """
        transactions = bbpsTransaction.objects.filter(user=request.user)
        serializer = bbpsTransactionSerializer(transactions, many=True)
        return Response({
            'success': True,
            'count': transactions.count(),
            'transactions': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def check_status(self, request):
        """
        Check transaction status
        POST /api/bbps/check_status/
        {
            "transaction_id": "RECH123456789"
        }
        """
        transaction_id = request.data.get('transaction_id')
        
        if not transaction_id:
            return Response({
                'success': False,
                'message': 'Transaction ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            txn = bbpsTransaction.objects.get(
                transaction_id=transaction_id,
                user=request.user
            )
            
            # If we have EKO transaction ref, check status via API
            if txn.eko_transaction_ref and txn.status in ['processing', 'pending']:
                result = bbps_manager.eko_service.check_status(txn.eko_transaction_ref)
                
                if isinstance(result, dict) and result.get('status') == 'success':
                    # Update transaction status based on API response
                    if result.get('data', {}).get('txstatus_desc', '').lower() == 'success':
                        txn.status = 'success'
                        txn.processed_at = timezone.now()
                        txn.completed_at = timezone.now()
                        txn.save()
            
            serializer = bbpsTransactionSerializer(txn)
            return Response({
                'success': True,
                'transaction': serializer.data
            })
            
        except bbpsTransaction.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Transaction not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Status check error: {str(e)}")
            return Response({
                'success': False,
                'message': f"Failed to check status: {str(e)}"

            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




    @staticmethod
    def get_all_child_users(user):
        role = user.role

        if role == "superadmin":
            return User.objects.all()

        if role == "admin":
            return User.objects.filter(
                Q(created_by=user) |
                Q(created_by__created_by=user) |
                Q(created_by__created_by__created_by=user) |
                Q(id=user.id)
            )

        if role == "master":
            return User.objects.filter(
                Q(created_by=user) |
                Q(created_by__created_by=user) |
                Q(id=user.id)
            )

        if role == "dealer":
            return User.objects.filter(
                Q(created_by=user) |
                Q(id=user.id)
            )

        return User.objects.filter(id=user.id)
    


    @action(detail=False, methods=['get'], url_path='bill_reports_history')
    def bill_reports_history(self, request):

        allowed_users = self.get_all_child_users(request.user)

        queryset = bbpsTransaction.objects.filter(
            user__in=allowed_users
        ).order_by('-initiated_at')

        # ----- Filters -----
        status_filter = request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        mobile_filter = request.GET.get('mobile')
        if mobile_filter:
            queryset = queryset.filter(mobile_number__icontains=mobile_filter)

        operator_filter = request.GET.get('operator_id')
        if operator_filter:
            queryset = queryset.filter(operator_id=operator_filter)

        date_from = request.GET.get('from')
        date_to = request.GET.get('to')
        if date_from:
            queryset = queryset.filter(initiated_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(initiated_at__date__lte=date_to)

        category = request.GET.get('category')
        if category:
            queryset = queryset.filter(operator_type=category)

        serializer = bbpsTransactionSerializer(queryset, many=True)

        return Response({
            "success": True,
            "count": queryset.count(),
            "reports": serializer.data
        })




class OperatorViewSet(viewsets.ReadOnlyModelViewSet):
    """Operator management"""
    permission_classes = [IsAuthenticated]
    queryset = Operator.objects.filter(is_active=True)
    serializer_class = OperatorSerializer
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get operators by type"""
        operator_type = request.query_params.get('type', 'prepaid')
        operators = self.get_queryset().filter(operator_type=operator_type)
        serializer = self.get_serializer(operators, many=True)
        return Response({
            'success': True,
            'count': operators.count(),
            'operators': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def with_plans(self, request):
        """Get operators with their plans"""
        operator_type = request.query_params.get('type', 'prepaid')
        operators = self.get_queryset().filter(
            operator_type=operator_type,
            plans__is_active=True
        ).distinct()
        
        result = []
        for operator in operators:
            plans = Plan.objects.filter(
                operator=operator,
                is_active=True
            ).order_by('amount')
            
            operator_data = OperatorSerializer(operator).data
            operator_data['plans'] = PlanSerializer(plans, many=True).data
            result.append(operator_data)
        
        return Response({
            'success': True,
            'operators': result
        })
    


    @action(detail=False, methods=['get'])
    def by_subcategory(self, request):
        """Get operators by service subcategory"""
        subcategory_id = request.query_params.get('subcategory_id')
        
        if not subcategory_id:
            return Response({
                'success': False,
                'message': 'subcategory_id parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from services.models import ServiceSubCategory
            subcategory = ServiceSubCategory.objects.get(id=subcategory_id)
            
            service_name_lower = subcategory.name.lower()
            
            if 'prepaid' in service_name_lower:
                operator_types = ['prepaid']
            elif 'postpaid' in service_name_lower:
                operator_types = ['postpaid']
            elif 'dth' in service_name_lower:
                operator_types = ['dth']
            elif 'electricity' in service_name_lower:
                operator_types = ['electricity']
            elif 'water' in service_name_lower:
                operator_types = ['water']
            elif 'gas' in service_name_lower:
                operator_types = ['gas']
            elif 'broadband' in service_name_lower:
                operator_types = ['broadband']
            elif 'landline' in service_name_lower:
                operator_types = ['landline']
            else:
                operator_types = self.queryset.values_list('operator_type', flat=True).distinct()
            
            operators = self.get_queryset().filter(operator_type__in=operator_types)
            serializer = self.get_serializer(operators, many=True)
            
            return Response({
                'success': True,
                'category': subcategory.name,
                'operators': serializer.data,
                'count': operators.count()
            })
            
        except ServiceSubCategory.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Service subcategory not found'
            }, status=status.HTTP_404_NOT_FOUND)

class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Plan management"""
    permission_classes = [IsAuthenticated]
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    
    @action(detail=False, methods=['get'])
    def by_operator(self, request):
        """Get plans by operator"""
        operator_id = request.query_params.get('operator_id')
        plan_type = request.query_params.get('plan_type')
        
        if not operator_id:
            return Response({
                'success': False,
                'message': 'operator_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.get_queryset().filter(operator__operator_id=operator_id)
        
        if plan_type:
            queryset = queryset.filter(plan_type=plan_type)
        
        # Sort by amount
        queryset = queryset.order_by('amount')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'plans': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def popular_plans(self, request):
        """Get popular plans"""
        operator_id = request.query_params.get('operator_id')
        plan_type = request.query_params.get('plan_type', 'combo')
        
        queryset = self.get_queryset().filter(
            is_popular=True,
            plan_type=plan_type
        )
        
        if operator_id:
            queryset = queryset.filter(operator__operator_id=operator_id)
        
        queryset = queryset.order_by('amount')[:20]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'plans': serializer.data
        })
