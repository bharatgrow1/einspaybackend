from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction as db_transaction
from django.db.models import Sum, Count, Q, Avg, Max, Min, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
import random
from decimal import InvalidOperation
from django.db.models.functions import ExtractMonth, ExtractYear
from rest_framework.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)


from commission.models import (CommissionPlan, ServiceCommission, UserCommissionPlan, CommissionPayout,  CommissionTransaction, OperatorCommission)
from commission.serializers import (CommissionPlanSerializer, ServiceCommissionSerializer, RoleFilteredServiceCommissionSerializer,
        BulkServiceCommissionCreateSerializer, CommissionTransactionSerializer, UserCommissionPlanSerializer,
        CommissionPayoutSerializer, DealerRetailerServiceCommissionSerializer, 
        AssignCommissionPlanSerializer, CommissionCalculatorSerializer, RoleBasedServiceCommissionSerializer, OperatorCommissionSerializer)

from users.models import (User, Wallet, Transaction)
from services.models import (ServiceCategory, ServiceSubCategory, ServiceSubmission)
from users.permissions import (IsAdminUser, IsSuperAdmin)
from services.serializers import (ServiceSubCategorySerializer, ServiceCategorySerializer)


class CommissionPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = CommissionPlan.objects.all()
    serializer_class = CommissionPlanSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class ServiceCommissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]  # Changed from [IsAuthenticated, IsAdminUser]
    queryset = ServiceCommission.objects.all()
    serializer_class = ServiceCommissionSerializer
    filter_fields = ['service_category', 'service_subcategory', 'commission_plan', 'is_active']
    
    def get_serializer_class(self):
        """Use different serializer based on user role"""
        user = self.request.user
        if user.role != 'superadmin':
            return RoleBasedServiceCommissionSerializer
        return ServiceCommissionSerializer
    
    def get_queryset(self):
        """Override get_queryset to add role-based filtering"""
        user = self.request.user
        user_role = user.role
        
        queryset = super().get_queryset()
        
        # Get role filter from query parameters (if any)
        role = self.request.query_params.get('role')
        
        if role:
            # Filter based on the specified role
            if role == 'admin':
                queryset = queryset.filter(admin_commission__gt=0)
            elif role == 'master':
                queryset = queryset.filter(master_commission__gt=0)
            elif role == 'dealer':
                queryset = queryset.filter(dealer_commission__gt=0)
            elif role == 'retailer':
                queryset = queryset.filter(retailer_commission__gt=0)
            elif role == 'superadmin':
                queryset = queryset.annotate(
                    total_distributed=(
                        F('admin_commission') + 
                        F('master_commission') + 
                        F('dealer_commission') + 
                        F('retailer_commission')
                    )
                ).filter(total_distributed__lt=100)
        else:
            # Apply role-based filtering automatically based on user's role
            if user_role == 'superadmin':
                # Super Admin sees all
                pass
            elif user_role == 'admin':
                # Admin sees Admin, Master, Dealer, Retailer
                queryset = queryset.filter(
                    Q(admin_commission__gt=0) |
                    Q(master_commission__gt=0) |
                    Q(dealer_commission__gt=0) |
                    Q(retailer_commission__gt=0)
                )
            elif user_role == 'master':
                # Master sees Master, Dealer, Retailer
                queryset = queryset.filter(
                    Q(master_commission__gt=0) |
                    Q(dealer_commission__gt=0) |
                    Q(retailer_commission__gt=0)
                )
            elif user_role == 'dealer':
                # Dealer sees Dealer, Retailer
                queryset = queryset.filter(
                    Q(dealer_commission__gt=0) |
                    Q(retailer_commission__gt=0)
                )
            elif user_role == 'retailer':
                # Retailer sees only Retailer
                queryset = queryset.filter(retailer_commission__gt=0)
        
        return queryset
    
    def get_serializer_context(self):
        """Pass request context to serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def check_permissions(self, request):
        """Check if user has permission for the action"""
        super().check_permissions(request)
        
        user = request.user
        user_role = user.role
        
        # Define allowed actions per role
        allowed_actions = {
            'superadmin': ['list', 'retrieve', 'create', 'update', 'partial_update', 'destroy'],
            'admin': ['list', 'retrieve', 'create', 'update', 'partial_update'],
            'master': ['list', 'retrieve', 'create', 'update', 'partial_update'],
            'dealer': ['list', 'retrieve', 'create', 'update', 'partial_update'],
            'retailer': ['list', 'retrieve']
        }
        
        action_name = self.action if self.action else 'list'
        
        if action_name not in allowed_actions.get(user_role, []):
            raise PermissionDenied(f"{user_role} cannot perform {action_name} action")
    
    def check_edit_permissions(self, user, data, instance=None):
        """Check if user has permission to edit specific commission fields"""
        user_role = user.role
        
        # Define editable fields for each role
        editable_fields_map = {
            'superadmin': ['admin_commission'],
            'admin': ['master_commission'],
            'master': ['dealer_commission'],
            'dealer': ['retailer_commission'],
            'retailer': []
        }
        
        editable_fields = editable_fields_map.get(user_role, [])
        
        # Check each field in data
        for field in data.keys():
            if field.endswith('_commission') and field != 'superadmin_commission':
                if field not in editable_fields:
                    raise PermissionDenied(
                        f"You do not have permission to edit {field}. "
                        f"As {user_role}, you can only edit: {', '.join(editable_fields)}"
                    )
        
        return True
    
    def perform_create(self, serializer):
        """Create commission with role-based permissions"""
        user = self.request.user
        user_role = user.role
        data = serializer.validated_data
        
        # Check edit permissions
        self.check_edit_permissions(user, data)
        
        # For non-superadmin users, preserve other commission values
        if user_role != 'superadmin':
            # Get existing commission for this service and plan
            service_subcategory = data.get('service_subcategory')
            service_category = data.get('service_category')
            commission_plan = data.get('commission_plan')
            
            existing_commission = ServiceCommission.objects.filter(
                Q(service_subcategory=service_subcategory) | Q(service_category=service_category),
                commission_plan=commission_plan
            ).first()
            
            if existing_commission:
                # For updates, preserve non-editable fields from existing commission
                if user_role == 'admin':
                    data['admin_commission'] = existing_commission.admin_commission
                elif user_role == 'master':
                    data['admin_commission'] = existing_commission.admin_commission
                    data['master_commission'] = existing_commission.master_commission
                elif user_role == 'dealer':
                    data['admin_commission'] = existing_commission.admin_commission
                    data['master_commission'] = existing_commission.master_commission
                    data['dealer_commission'] = existing_commission.dealer_commission
            else:
                # For new commissions, set defaults for non-editable fields
                if user_role == 'admin':
                    data['admin_commission'] = 0
                elif user_role == 'master':
                    data['admin_commission'] = 0
                    data['master_commission'] = 0
                elif user_role == 'dealer':
                    data['admin_commission'] = 0
                    data['master_commission'] = 0
                    data['dealer_commission'] = 0
        
        serializer.save(created_by=user)
    
    def perform_update(self, serializer):
        """Update commission with role-based permissions"""
        user = self.request.user
        user_role = user.role
        data = serializer.validated_data
        instance = self.get_object()
        
        # Check edit permissions
        self.check_edit_permissions(user, data)
        
        # For partial updates, preserve fields user cannot edit
        if user_role != 'superadmin':
            # Get the original instance values
            original_data = {
                'admin_commission': instance.admin_commission,
                'master_commission': instance.master_commission,
                'dealer_commission': instance.dealer_commission,
                'retailer_commission': instance.retailer_commission
            }
            
            # Preserve fields based on role
            if user_role == 'admin':
                # Admin can only edit master_commission
                data['admin_commission'] = original_data['admin_commission']
                if 'dealer_commission' in data:
                    data['dealer_commission'] = original_data['dealer_commission']
                if 'retailer_commission' in data:
                    data['retailer_commission'] = original_data['retailer_commission']
            elif user_role == 'master':
                # Master can only edit dealer_commission
                data['admin_commission'] = original_data['admin_commission']
                data['master_commission'] = original_data['master_commission']
                if 'retailer_commission' in data:
                    data['retailer_commission'] = original_data['retailer_commission']
            elif user_role == 'dealer':
                # Dealer can only edit retailer_commission
                data['admin_commission'] = original_data['admin_commission']
                data['master_commission'] = original_data['master_commission']
                data['dealer_commission'] = original_data['dealer_commission']
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only superadmin can delete commissions"""
        user = self.request.user
        if user.role != 'superadmin':
            raise PermissionDenied("Only Super Admin can delete commissions")
        instance.delete()
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple service commissions at once with individual data"""
        user = request.user
        user_role = user.role
        
        serializer = BulkServiceCommissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        created_count = 0
        errors = []
        
        for commission_data in serializer.validated_data['commissions']:
            try:
                # Check permissions for this commission
                self.check_edit_permissions(user, commission_data)
                
                service_subcategory_id = commission_data.get('service_subcategory')
                commission_plan_id = commission_data.get('commission_plan')
                service_category_id = commission_data.get('service_category')
                
                # Find existing commission
                existing_commission = ServiceCommission.objects.filter(
                    Q(service_subcategory_id=service_subcategory_id) | Q(service_category_id=service_category_id),
                    commission_plan_id=commission_plan_id
                ).first()
                
                if existing_commission:
                    # Update existing commission
                    commission_serializer = ServiceCommissionSerializer(
                        existing_commission, 
                        data=commission_data,
                        partial=True,
                        context={'request': request}
                    )
                else:
                    # Create new commission
                    commission_serializer = ServiceCommissionSerializer(
                        data=commission_data,
                        context={'request': request}
                    )
                
                if commission_serializer.is_valid():
                    # For new commissions by non-superadmin, set defaults
                    if not existing_commission and user_role != 'superadmin':
                        if user_role == 'admin':
                            commission_data['admin_commission'] = 0
                        elif user_role == 'master':
                            commission_data['admin_commission'] = 0
                            commission_data['master_commission'] = 0
                        elif user_role == 'dealer':
                            commission_data['admin_commission'] = 0
                            commission_data['master_commission'] = 0
                            commission_data['dealer_commission'] = 0
                    
                    commission_serializer.save(created_by=user)
                    created_count += 1
                else:
                    errors.append(f"Validation error for service {service_subcategory_id}: {commission_serializer.errors}")
                    
            except PermissionDenied as e:
                errors.append(f"Permission error for service {commission_data.get('service_subcategory')}: {str(e)}")
            except Exception as e:
                errors.append(f"Error creating commission for service {commission_data.get('service_subcategory')}: {str(e)}")
        
        response_data = {
            'message': f'Successfully processed {created_count} commissions',
            'created_count': created_count,
            'errors': errors
        }
        
        if errors:
            response_data['has_errors'] = True
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def my_permissions(self, request):
        """Get current user's commission permissions"""
        user = request.user
        user_role = user.role
        
        permissions = {
            'user_role': user_role,
            'can_view': [],
            'can_edit': [],
            'can_delete': user_role == 'superadmin',
            'description': ''
        }
        
        # Define permissions based on role
        if user_role == 'superadmin':
            permissions['can_view'] = ['admin', 'master', 'dealer', 'retailer', 'superadmin']
            permissions['can_edit'] = ['admin_commission']
            permissions['description'] = 'Can view all commissions, edit only Admin commission'
        elif user_role == 'admin':
            permissions['can_view'] = ['admin', 'master', 'dealer', 'retailer']
            permissions['can_edit'] = ['master_commission']
            permissions['description'] = 'Can view Admin to Retailer commissions, edit only Master commission'
        elif user_role == 'master':
            permissions['can_view'] = ['master', 'dealer', 'retailer']
            permissions['can_edit'] = ['dealer_commission']
            permissions['description'] = 'Can view Master to Retailer commissions, edit only Dealer commission'
        elif user_role == 'dealer':
            permissions['can_view'] = ['dealer', 'retailer']
            permissions['can_edit'] = ['retailer_commission']
            permissions['description'] = 'Can view Dealer and Retailer commissions, edit only Retailer commission'
        elif user_role == 'retailer':
            permissions['can_view'] = ['retailer']
            permissions['can_edit'] = []
            permissions['description'] = 'Can view only Retailer commission, cannot edit any'
        
        return Response(permissions)
    
    @action(detail=True, methods=['get'])
    def distribution_details(self, request, pk=None):
        """Get detailed distribution information for a service commission"""
        service_commission = self.get_object()
        user = request.user
        user_role = user.role
        
        distribution_percentages = service_commission.get_distribution_percentages()
        
        # Filter what user can see based on role
        filtered_distribution = {}
        for role, percentage in distribution_percentages.items():
            if role == 'superadmin':
                filtered_distribution[role] = percentage
            elif role == 'admin' and user_role in ['superadmin', 'admin']:
                filtered_distribution[role] = percentage
            elif role == 'master' and user_role in ['superadmin', 'admin', 'master']:
                filtered_distribution[role] = percentage
            elif role == 'dealer' and user_role in ['superadmin', 'admin', 'master', 'dealer']:
                filtered_distribution[role] = percentage
            elif role == 'retailer' and user_role in ['superadmin', 'admin', 'master', 'dealer', 'retailer']:
                filtered_distribution[role] = percentage
        
        return Response({
            'service_commission_id': service_commission.id,
            'service_name': service_commission.service_subcategory.name if service_commission.service_subcategory else service_commission.service_category.name,
            'commission_plan': service_commission.commission_plan.name,
            'commission_type': service_commission.commission_type,
            'commission_value': service_commission.commission_value,
            'distribution_percentages': filtered_distribution,
            'total_distributed': sum([
                service_commission.admin_commission,
                service_commission.master_commission,
                service_commission.dealer_commission,
                service_commission.retailer_commission
            ]),
            'superadmin_share': distribution_percentages['superadmin']
        })
    

class CommissionTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CommissionTransactionSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = CommissionTransaction.objects.all()
        
        # Apply role-based filtering
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Apply date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date
                )
            except ValueError:
                pass
        
        if user.is_admin_user():
            return queryset
        
        return queryset.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def my_commissions(self, request):
        """Get current user's commissions with stats"""
        user = request.user
        
        # Get filter parameters
        role = request.query_params.get('role')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Base queryset
        commission_qs = CommissionTransaction.objects.filter(
            user=user, 
            status='success',
            transaction_type='credit'
        )
        
        # Apply filters
        if role:
            commission_qs = commission_qs.filter(role=role)
        
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                commission_qs = commission_qs.filter(
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date
                )
            except ValueError:
                pass
        
        total_commission = commission_qs.aggregate(total=Sum('commission_amount'))['total'] or 0
        
        # Commission by role breakdown
        commission_by_role = CommissionTransaction.objects.filter(
            user=user,
            status='success',
            transaction_type='credit'
        ).values('role').annotate(
            total=Sum('commission_amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Recent commissions
        recent_commissions = commission_qs.order_by('-created_at')[:10]
        
        # Fixed monthly breakdown for current year - using ExtractMonth
        current_year = timezone.now().year
        monthly_data = CommissionTransaction.objects.filter(
            user=user,
            status='success',
            transaction_type='credit',
            created_at__year=current_year
        ).annotate(
            month=ExtractMonth('created_at')
        ).values('month').annotate(
            total=Sum('commission_amount')
        ).order_by('month')
        
        serializer = self.get_serializer(recent_commissions, many=True)
        
        return Response({
            'total_commission': total_commission,
            'commission_by_role': list(commission_by_role),
            'recent_commissions': serializer.data,
            'monthly_breakdown': list(monthly_data),
            'filters_applied': {
                'role': role,
                'start_date': start_date,
                'end_date': end_date
            }
        })
    
    @action(detail=False, methods=['get'])
    def role_stats(self, request):
        """Get commission statistics by role for current user"""
        user = request.user
        
        role_stats = CommissionTransaction.objects.filter(
            user=user,
            status='success',
            transaction_type='credit'
        ).values('role').annotate(
            total_commission=Sum('commission_amount'),
            transaction_count=Count('id'),
            avg_commission=Avg('commission_amount')
        ).order_by('-total_commission')
        
        return Response({
            'role_stats': list(role_stats),
            'user_role': user.role
        })
    

    @action(detail=False, methods=['post'])
    def process_commission_manually(self, request):
        """Manually process commission for a service submission"""
        submission_id = request.data.get('submission_id')
        
        if not submission_id:
            return Response(
                {'error': 'submission_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            submission = ServiceSubmission.objects.get(id=submission_id)
            transaction = Transaction.objects.filter(
                service_submission=submission,
                status='success'
            ).first()
            
            if not transaction:
                return Response(
                    {'error': 'No successful transaction found for this submission'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            success, message = CommissionManager.process_service_commission(
                submission, transaction
            )
            
            if success:
                # Check wallet balances after commission distribution
                commission_transactions = CommissionTransaction.objects.filter(
                    service_submission=submission
                )
                
                wallet_updates = []
                for ct in commission_transactions:
                    wallet = ct.user.wallet
                    wallet_updates.append({
                        'user': ct.user.username,
                        'role': ct.role,
                        'commission_amount': ct.commission_amount,
                        'wallet_balance': wallet.balance
                    })
                
                serializer = CommissionTransactionSerializer(commission_transactions, many=True)
                
                return Response({
                    'message': message,
                    'commission_transactions': serializer.data,
                    'wallet_updates': wallet_updates,
                    'total_commissions': commission_transactions.count()
                })
            else:
                return Response(
                    {'error': message}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except ServiceSubmission.DoesNotExist:
            return Response(
                {'error': 'Service submission not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class UserCommissionPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = UserCommissionPlan.objects.all()
    serializer_class = UserCommissionPlanSerializer
    
    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def assign_plan(self, request):
        """Assign commission plan to multiple users"""
        serializer = AssignCommissionPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_ids = serializer.validated_data['user_ids']
        commission_plan_id = serializer.validated_data['commission_plan_id']
        
        try:
            commission_plan = CommissionPlan.objects.get(id=commission_plan_id)
        except CommissionPlan.DoesNotExist:
            return Response(
                {'error': 'Commission plan not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        assigned_count = 0
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                UserCommissionPlan.objects.update_or_create(
                    user=user,
                    defaults={
                        'commission_plan': commission_plan,
                        'assigned_by': request.user,
                        'is_active': True
                    }
                )
                assigned_count += 1
            except User.DoesNotExist:
                continue
        
        return Response({
            'message': f'Commission plan assigned to {assigned_count} users',
            'assigned_count': assigned_count
        })
    
    @action(detail=False, methods=['get'])
    def user_plan(self, request):
        """Get current user's commission plan"""
        try:
            user_plan = UserCommissionPlan.objects.get(user=request.user, is_active=True)
            serializer = self.get_serializer(user_plan)
            return Response(serializer.data)
        except UserCommissionPlan.DoesNotExist:
            return Response({
                'message': 'No active commission plan assigned',
                'has_plan': False
            })

class CommissionPayoutViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = CommissionPayout.objects.all()
    serializer_class = CommissionPayoutSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user role if provided
        user_role = self.request.query_params.get('user_role')
        if user_role:
            queryset = queryset.filter(user__role=user_role)
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def process_payout(self, request, pk=None):
        """Process commission payout"""
        payout = self.get_object()
        
        if payout.status != 'pending':
            return Response(
                {'error': 'Payout already processed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with db_transaction.atomic():
                wallet = payout.user.wallet
                wallet.balance += payout.total_amount
                wallet.save()
                
                Transaction.objects.create(
                    wallet=wallet,
                    amount=payout.total_amount,
                    transaction_type='credit',
                    transaction_category='commission',
                    description=f"Commission payout {payout.reference_number}",
                    created_by=request.user
                )
                
                payout.status = 'completed'
                payout.processed_by = request.user
                payout.processed_at = timezone.now()
                payout.save()
                
                return Response({
                    'message': 'Payout processed successfully',
                    'payout': CommissionPayoutSerializer(payout).data
                })
                
        except Exception as e:
            return Response(
                {'error': f'Payout processing failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CommissionCalculatorView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Calculate commission for a transaction"""
        serializer = CommissionCalculatorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service_subcategory_id = serializer.validated_data['service_subcategory_id']
        transaction_amount = serializer.validated_data['transaction_amount']
        user_id = serializer.validated_data.get('user_id', request.user.id)
        
        try:
            user = User.objects.get(id=user_id)
            service_subcategory = ServiceSubCategory.objects.get(id=service_subcategory_id)
            
            try:
                user_plan = UserCommissionPlan.objects.get(user=user, is_active=True)
                commission_plan = user_plan.commission_plan
            except UserCommissionPlan.DoesNotExist:
                return Response(
                    {'error': 'No active commission plan assigned to user'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            commission_config = ServiceCommission.objects.get(
                service_subcategory=service_subcategory,
                commission_plan=commission_plan,
                is_active=True
            )
            
            distribution, hierarchy_users = commission_config.distribute_commission(
                transaction_amount, user
            )
            
            distribution_percentages = commission_config.get_distribution_percentages()
            
            return Response({
                'transaction_amount': transaction_amount,
                'service': service_subcategory.name,
                'commission_plan': commission_plan.name,
                'total_commission': commission_config.calculate_commission(transaction_amount),
                'distribution_amounts': distribution,
                'distribution_percentages': distribution_percentages,
                'hierarchy_users': {
                    role: {
                        'username': user.username if user else 'N/A',
                        'user_id': user.id if user else None,
                        'role': role
                    } for role, user in hierarchy_users.items()
                }
            })
            
        except (User.DoesNotExist, ServiceSubCategory.DoesNotExist, ServiceCommission.DoesNotExist) as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )

class CommissionStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get commission statistics overview with role-based filtering"""
        
        # Get filter parameters
        role = request.query_params.get('role')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Base queryset
        commission_qs = CommissionTransaction.objects.filter(
            status='success', 
            transaction_type='credit'
        )
        
        # Apply filters
        if role:
            commission_qs = commission_qs.filter(role=role)
        
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                commission_qs = commission_qs.filter(
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date
                )
            except ValueError:
                pass
        
        total_commission = commission_qs.aggregate(total=Sum('commission_amount'))['total'] or 0
        
        pending_payouts = CommissionPayout.objects.filter(
            status='pending'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        total_payouts = CommissionPayout.objects.filter(
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        commission_by_role = commission_qs.values('role').annotate(
            total=Sum('commission_amount'),
            count=Count('id')
        ).order_by('-total')
        
        top_services = commission_qs.values(
            'service_submission__service_form__name'
        ).annotate(
            total=Sum('commission_amount'),
            count=Count('id')
        ).order_by('-total')[:10]
        
        return Response({
            'total_commission': total_commission,
            'pending_payouts': pending_payouts,
            'total_payouts': total_payouts,
            'commission_by_role': list(commission_by_role),
            'top_services': list(top_services),
            'filters_applied': {
                'role': role,
                'start_date': start_date,
                'end_date': end_date
            }
        })
    
    @action(detail=False, methods=['get'])
    def role_performance(self, request):
        """Get detailed performance statistics by role"""
        
        role_stats = CommissionTransaction.objects.filter(
            status='success',
            transaction_type='credit'
        ).values('role').annotate(
            total_commission=Sum('commission_amount'),
            transaction_count=Count('id'),
            avg_commission=Avg('commission_amount'),
            max_commission=Max('commission_amount'),
            min_commission=Min('commission_amount')
        ).order_by('-total_commission')
        
        # User count by role
        user_count_by_role = User.objects.filter(
            is_active=True
        ).exclude(role__in=['superadmin']).values('role').annotate(
            user_count=Count('id')
        )
        
        return Response({
            'role_performance': list(role_stats),
            'user_distribution': list(user_count_by_role)
        })


class CommissionManager:
    @staticmethod
    def process_operator_commission(bbps_txn, wallet_transaction, operator_id):
        """Process commission for a bbps transaction based on operator"""
        try:
            with db_transaction.atomic():
                retailer_user = bbps_txn.user
                transaction_amount = bbps_txn.amount
                
                # Get retailer's commission plan
                try:
                    user_plan = UserCommissionPlan.objects.get(user=retailer_user, is_active=True)
                    commission_plan = user_plan.commission_plan
                except UserCommissionPlan.DoesNotExist:
                    return False, "No active commission plan for user"
                
                # Find operator commission configuration
                operator_commission = None
                try:
                    # First try with specific circle
                    operator_commission = OperatorCommission.objects.get(
                        operator__operator_id=operator_id,
                        commission_plan=commission_plan,
                        operator_circle=bbps_txn.circle,  # bbps_txn से circle लें
                        is_active=True
                    )
                except OperatorCommission.DoesNotExist:
                    # Try without circle (generic)
                    try:
                        operator_commission = OperatorCommission.objects.get(
                            operator__operator_id=operator_id,
                            commission_plan=commission_plan,
                            operator_circle__isnull=True,
                            is_active=True
                        )
                    except OperatorCommission.DoesNotExist:
                        return False, "No commission configuration found for this operator"
                
                # Calculate distribution
                distribution, hierarchy_users = operator_commission.distribute_commission(
                    transaction_amount, retailer_user
                )
                
                total_commission_distributed = 0
                
                for role, amount in distribution.items():
                    if amount > 0 and hierarchy_users[role]:
                        recipient_user = hierarchy_users[role]
                        
                        # Ensure wallet exists
                        recipient_wallet, created = Wallet.objects.get_or_create(user=recipient_user)
                        
                        # Create commission transaction
                        commission_txn = CommissionTransaction.objects.create(
                            main_transaction=wallet_transaction,  # wallet transaction use करें
                            operator_commission=operator_commission,
                            commission_plan=commission_plan,
                            user=recipient_user,
                            role=role,
                            commission_amount=amount,
                            transaction_type='credit',
                            status='success',
                            description=f"Commission for {operator_commission.operator_name} bbps - {role}",
                            retailer_user=retailer_user,
                            original_transaction_amount=transaction_amount
                        )
                        
                        # Add to wallet balance
                        recipient_wallet.balance += amount
                        recipient_wallet.save()
                        
                        # Create wallet transaction
                        Transaction.objects.create(
                            wallet=recipient_wallet,
                            amount=amount,
                            net_amount=amount,
                            service_charge=0,
                            transaction_type='credit',
                            transaction_category='commission',
                            description=f"Commission from {operator_commission.operator_name} bbps as {role}",
                            created_by=recipient_user,
                            status='success'
                        )
                        
                        total_commission_distributed += amount
                
                return True, f"Operator commission processed successfully. Total: ₹{total_commission_distributed}"
                
        except Exception as e:
            import traceback
            logger.error(f"Commission processing error: {str(e)}\n{traceback.format_exc()}")
            return False, f"Operator commission processing failed: {str(e)}"


class DealerRetailerCommissionViewSet(viewsets.ReadOnlyModelViewSet):
    """View for dealers and retailers to see their commission rates"""
    permission_classes = [IsAuthenticated]
    serializer_class = DealerRetailerServiceCommissionSerializer
    
    def get_queryset(self):
        """Only show services where the user's role gets commission with filtering"""
        user = self.request.user
        user_role = user.role
        
        # Only allow dealer and retailer roles
        if user_role not in ['dealer', 'retailer']:
            return ServiceCommission.objects.none()
        
        queryset = ServiceCommission.objects.filter(is_active=True)
        
        # Filter based on user's role
        if user_role == 'dealer':
            queryset = queryset.filter(dealer_commission__gt=0)
        elif user_role == 'retailer':
            queryset = queryset.filter(retailer_commission__gt=0)
        
        # Apply category and subcategory filtering
        service_category_id = self.request.query_params.get('service_category')
        if service_category_id:
            queryset = queryset.filter(service_category_id=service_category_id)
        
        service_subcategory_id = self.request.query_params.get('service_subcategory')
        if service_subcategory_id:
            queryset = queryset.filter(service_subcategory_id=service_subcategory_id)
        
        # Apply commission plan filtering if needed
        commission_plan_id = self.request.query_params.get('commission_plan')
        if commission_plan_id:
            queryset = queryset.filter(commission_plan_id=commission_plan_id)
        
        return queryset
    
    def get_serializer_context(self):
        """Pass request context to serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=False, methods=['get'])
    def my_commission_summary(self, request):
        """Get summary of commission rates for current user with filtering"""
        user = request.user
        user_role = user.role
        
        if user_role not in ['dealer', 'retailer']:
            return Response(
                {'error': 'This endpoint is only for dealers and retailers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        
        # Get filter counts
        total_services = queryset.count()
        
        # Get unique categories and subcategories for the filtered results
        categories = ServiceCategory.objects.filter(
            id__in=queryset.values_list('service_category_id', flat=True).distinct()
        )
        
        subcategories = ServiceSubCategory.objects.filter(
            id__in=queryset.values_list('service_subcategory_id', flat=True).distinct()
        )
        
        summary_data = []
        for commission in queryset:
            distribution_percentages = commission.get_distribution_percentages()
            user_percentage = distribution_percentages.get(user_role, 0)
            
            service_data = {
                'service_id': commission.service_subcategory.id if commission.service_subcategory else commission.service_category.id,
                'service_name': commission.service_subcategory.name if commission.service_subcategory else commission.service_category.name,
                'service_category': commission.service_category.name if commission.service_category else 'N/A',
                'service_category_id': commission.service_category.id if commission.service_category else None,
                'service_subcategory_id': commission.service_subcategory.id if commission.service_subcategory else None,
                'total_commission_rate': commission.commission_value,
                'commission_type': commission.commission_type,
                'your_commission_percentage': user_percentage,
                'commission_plan': commission.commission_plan.name,
                'is_active': commission.is_active
            }
            summary_data.append(service_data)
        
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user_role
            },
            'total_services': total_services,
            'available_categories': ServiceCategorySerializer(categories, many=True).data,
            'available_subcategories': ServiceSubCategorySerializer(subcategories, many=True).data,
            'commission_rates': summary_data,
            'filters_applied': {
                'service_category': request.query_params.get('service_category'),
                'service_subcategory': request.query_params.get('service_subcategory'),
                'commission_plan': request.query_params.get('commission_plan')
            }
        })
    


class CommissionDashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_commission_dashboard(self, request):
        """Get comprehensive commission dashboard for current user"""
        user = request.user
        
        # Basic stats
        total_commission = CommissionTransaction.objects.filter(
            user=user, status='success', transaction_type='credit'
        ).aggregate(total=Sum('commission_amount'))['total'] or 0
        
        today_commission = CommissionTransaction.objects.filter(
            user=user, status='success', transaction_type='credit',
            created_at__date=timezone.now().date()
        ).aggregate(total=Sum('commission_amount'))['total'] or 0
        
        # Fixed monthly breakdown - using Django's ExtractMonth instead of raw SQL
        monthly_data = CommissionTransaction.objects.filter(
            user=user, status='success', transaction_type='credit',
            created_at__year=timezone.now().year
        ).annotate(
            month=ExtractMonth('created_at')
        ).values('month').annotate(
            total=Sum('commission_amount'),
            count=Count('id')
        ).order_by('month')
        
        # Top performing services
        top_services = CommissionTransaction.objects.filter(
            user=user, status='success', transaction_type='credit'
        ).values(
            'service_submission__service_subcategory__name'
        ).annotate(
            total=Sum('commission_amount'),
            count=Count('id')
        ).order_by('-total')[:5]
        
        # Recent commissions
        recent_commissions = CommissionTransaction.objects.filter(
            user=user, status='success', transaction_type='credit'
        ).select_related(
            'service_submission', 'service_submission__service_subcategory'
        ).order_by('-created_at')[:10]
        
        # Hierarchy stats (for users who have downline)
        if user.role in ['superadmin', 'admin', 'master', 'dealer']:
            downline_users = User.objects.filter(created_by=user)
            downline_commission = CommissionTransaction.objects.filter(
                user__in=downline_users, status='success', transaction_type='credit'
            ).aggregate(total=Sum('commission_amount'))['total'] or 0
        else:
            downline_commission = 0
        
        return Response({
            'user': {
                'username': user.username,
                'role': user.role,
                'wallet_balance': user.wallet.balance
            },
            'commission_stats': {
                'total_commission': total_commission,
                'today_commission': today_commission,
                'downline_commission': downline_commission,
                'total_transactions': CommissionTransaction.objects.filter(
                    user=user, status='success', transaction_type='credit'
                ).count()
            },
            'monthly_breakdown': list(monthly_data),
            'top_services': list(top_services),
            'recent_commissions': CommissionTransactionSerializer(
                recent_commissions, many=True
            ).data
        })
    


class OperatorCommissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = (OperatorCommission.objects.select_related('operator', 'commission_plan', 'service_subcategory'))
    serializer_class = OperatorCommissionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()

        service_subcategory_id = self.request.query_params.get('service_subcategory')
        if service_subcategory_id:
            queryset = queryset.filter(service_subcategory_id=service_subcategory_id)

        operator_type = self.request.query_params.get('operator_type')
        if operator_type:
            queryset = queryset.filter(operator_type=operator_type)

        operator_id = self.request.query_params.get('operator_id')
        if operator_id:
            queryset = queryset.filter(operator_id=operator_id)

        circle = self.request.query_params.get('circle')
        if circle:
            queryset = queryset.filter(operator_circle=circle)

        commission_plan = self.request.query_params.get('commission_plan')
        if commission_plan:
            queryset = queryset.filter(commission_plan_id=commission_plan)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset


    
    def perform_create(self, serializer):
        operator = serializer.validated_data.get('operator')
        service_subcategory = serializer.validated_data.get('service_subcategory')

        serializer.save(
            operator_name=operator.operator_name,
            operator_type=operator.operator_type,
            service_subcategory=service_subcategory,
            created_by=self.request.user
        )

    
    @action(detail=False, methods=['get'])
    def operator_types(self, request):
        """Get all unique operator types"""
        from bbps.models import Operator
        
        operator_types = Operator.objects.values_list(
            'operator_type', flat=True
        ).distinct().order_by('operator_type')
        
        return Response({
            'operator_types': list(operator_types)
        })
    
    
    @action(detail=False, methods=['get'])
    def available_operators(self, request):
        """Get operators filtered by service subcategory"""
        service_subcategory_id = request.query_params.get('service_subcategory')
        
        if not service_subcategory_id:
            return Response({
                'error': 'service_subcategory parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from services.models import ServiceSubCategory
            subcategory = ServiceSubCategory.objects.get(id=service_subcategory_id)
            
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
                from bbps.models import Operator
                operator_types = list(Operator.objects.values_list('operator_type', flat=True).distinct())
            
            from bbps.models import Operator
            queryset = Operator.objects.filter(
                is_active=True,
                operator_type__in=operator_types
            )
            
            from bbps.serializers import OperatorSerializer
            serializer = OperatorSerializer(queryset, many=True)
            
            return Response({
                'success': True,
                'service_name': subcategory.name,
                'operator_types': operator_types,
                'operators': serializer.data,
                'count': queryset.count()
            })
            
        except ServiceSubCategory.DoesNotExist:
            return Response({
                'error': 'Service subcategory not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    
    @action(detail=False, methods=['post'])
    def bulk_create_operator_commissions(self, request):
        """Create multiple operator commissions at once"""
        user = request.user
        
        serializer = BulkServiceCommissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        created_count = 0
        errors = []
        
        for commission_data in serializer.validated_data['commissions']:
            try:
                # Convert service_subcategory to operator
                operator_id = commission_data.get('operator')
                commission_plan_id = commission_data.get('commission_plan')
                operator_circle = commission_data.get('operator_circle')
                
                # Check if commission already exists
                existing_commission = OperatorCommission.objects.filter(
                    operator_id=operator_id,
                    commission_plan_id=commission_plan_id,
                    operator_circle=operator_circle
                ).first()
                
                if existing_commission:
                    # Update existing commission
                    commission_serializer = OperatorCommissionSerializer(
                        existing_commission, 
                        data=commission_data,
                        partial=True
                    )
                else:
                    # Create new commission
                    commission_serializer = OperatorCommissionSerializer(
                        data=commission_data
                    )
                
                if commission_serializer.is_valid():
                    commission_serializer.save(created_by=user)
                    created_count += 1
                else:
                    errors.append(f"Validation error for operator {operator_id}: {commission_serializer.errors}")
                    
            except Exception as e:
                errors.append(f"Error creating commission for operator {commission_data.get('operator')}: {str(e)}")
        
        response_data = {
            'message': f'Successfully processed {created_count} operator commissions',
            'created_count': created_count,
            'errors': errors
        }
        
        if errors:
            response_data['has_errors'] = True
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def commission_by_operator_type(self, request):
        """Get commissions grouped by operator type"""
        operator_type = request.query_params.get('operator_type', 'prepaid')
        
        commissions = self.get_queryset().filter(
            operator__operator_type=operator_type
        ).select_related('operator', 'commission_plan')
        
        # Group by operator
        operators = {}
        for commission in commissions:
            operator_key = f"{commission.operator.operator_id}_{commission.operator_circle or 'all'}"
            
            if operator_key not in operators:
                operators[operator_key] = {
                    'operator_id': commission.operator.operator_id,
                    'operator_name': commission.operator.operator_name,
                    'operator_type': commission.operator.operator_type,
                    'circle': commission.operator_circle,
                    'commissions': []
                }
            
            operators[operator_key]['commissions'].append({
                'id': commission.id,
                'commission_plan': commission.commission_plan.name,
                'commission_type': commission.commission_type,
                'commission_value': commission.commission_value,
                'admin_commission': commission.admin_commission,
                'master_commission': commission.master_commission,
                'dealer_commission': commission.dealer_commission,
                'retailer_commission': commission.retailer_commission,
                'is_active': commission.is_active
            })
        
        return Response({
            'operator_type': operator_type,
            'operators': list(operators.values())
        })
